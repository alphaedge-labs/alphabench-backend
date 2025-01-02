from typing import List, Optional
from uuid import UUID

from src.db.base import execute_query, execute_query_single

def create_backtest_request(db, user_id: UUID, backtest: dict) -> dict:
    """Create a new backtest request"""
    return execute_query_single(
        db,
        """
        INSERT INTO backtest_requests (
            user_id, instrument_symbol, from_date, to_date,
            strategy_description, strategy_title
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            user_id,
            backtest['instrument_symbol'],
            backtest['from_date'],
            backtest['to_date'],
            backtest['strategy_description'],
            backtest.get('strategy_title')
        )
    )

def get_user_backtests(db, user_id: UUID) -> List[dict]:
    """Get all backtest requests for a user"""
    return execute_query(
        db,
        """
        SELECT * FROM backtest_requests
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

def get_backtest_by_id(db, backtest_id: UUID) -> Optional[dict]:
    """Get a specific backtest request"""
    return execute_query_single(
        db,
        """
        SELECT * FROM backtest_requests
        WHERE id = %s
        """,
        (backtest_id,)
    )

def update_backtest_status(db, backtest_id: UUID, status: str, error_message: Optional[str] = None) -> dict:
    """Update backtest status and error message"""
    return execute_query_single(
        db,
        """
        UPDATE backtest_requests
        SET status = %s,
            error_message = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING *
        """,
        (status, error_message, backtest_id)
    )

def update_backtest_urls(
    db,
    backtest_id: UUID,
    python_script_url: Optional[str] = None,
    validation_data_url: Optional[str] = None,
    full_data_url: Optional[str] = None,
    log_file_url: Optional[str] = None,
    report_url: Optional[str] = None
) -> dict:
    """Update backtest file URLs"""
    return execute_query_single(
        db,
        """
        UPDATE backtest_requests
        SET python_script_url = COALESCE(%s, python_script_url),
            validation_data_url = COALESCE(%s, validation_data_url),
            full_data_url = COALESCE(%s, full_data_url),
            log_file_url = COALESCE(%s, log_file_url),
            report_url = COALESCE(%s, report_url),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING *
        """,
        (
            python_script_url,
            validation_data_url,
            full_data_url,
            log_file_url,
            report_url,
            backtest_id
        )
    )
