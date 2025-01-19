from psycopg2 import sql
from typing import List
from datetime import datetime
import pandas as pd

from src.db.base import execute_query

from src.utils.logger import get_logger
logger = get_logger(__name__)

def get_available_columns(
    conn,
    instrument_symbol: str,
    from_date: datetime,
    to_date: datetime
) -> List[str]:
    """Get available columns and their non-null count for a given instrument and date range"""
    try:
        # First get all column names
        columns = execute_query(
            conn,
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'tick_data'"
        )
        
        if not columns:
            return []
            
        available_columns = []
        
        # Check each column for non-null values
        for col in columns:
            column_name = col['column_name']
            query = sql.SQL("""
                SELECT 1 
                FROM tick_data t
                WHERE t.ticker = %s
                AND t.time BETWEEN %s AND %s
                AND t.{} IS NOT NULL
                LIMIT 1
            """).format(sql.Identifier(column_name))
            
            result = execute_query(conn, query, (instrument_symbol, from_date, to_date))
            if result:
                available_columns.append(column_name)
        
        return available_columns
        
    except Exception as e:
        conn.rollback()
        logger.warning(f'Error getting available columns: {e}')
        return []

def fetch_tick_data(
    conn,
    instrument_symbol: str,
    from_date: datetime,
    to_date: datetime,
    columns: List[str] = None
) -> pd.DataFrame:
    """
    Fetch tick data for a given instrument and date range
    
    Args:
        conn: Database connection
        instrument_symbol: The ticker symbol
        from_date: Start date
        to_date: End date
        columns: List of columns to fetch (optional)
    
    Returns:
        DataFrame containing the tick data or empty DataFrame on error
    """
    try:
        columns_str = "*" if columns is None else ", ".join(columns)
        
        result = execute_query(
            conn,
            f"""
            SELECT {columns_str}
            FROM tick_data
            WHERE ticker = %s
            AND time BETWEEN %s AND %s
            ORDER BY time
            """,
            (instrument_symbol, from_date, to_date)
        )
        
        # Convert to DataFrame
        if result:
            df = pd.DataFrame(result, columns=columns if columns else get_column_names(result))
            return df
        return pd.DataFrame()
        
    except Exception as e:
        conn.rollback()
        logger.warning(f'Error fetching tick data: {e}')
        return pd.DataFrame()

def get_column_names(result_set):
    """Helper function to get column names from result set description"""
    return [desc[0] for desc in result_set.description] if result_set.description else []