from typing import List, Optional
from uuid import UUID
import logging
import asyncio

from src.db.base import execute_query, execute_query_single

from src.api.services.postbacks import (
    post_backtest_update
)

logger = logging.getLogger()

def create_backtest_request(conn, user_id: UUID, backtest: dict) -> dict:
    """Create a new backtest request"""
    try:
        result = execute_query_single(
            conn,
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
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to create backtest request: {str(e)}")

def get_user_backtests(conn, user_id: UUID) -> List[dict]:
    """Get all backtest requests for a user"""
    result = execute_query(
        conn,
        """
        SELECT * FROM backtest_requests
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )
    return result

def get_backtest_by_id(conn, backtest_id: UUID) -> Optional[dict]:
    """Get a specific backtest request"""
    try:
        result = execute_query_single(
            conn,
            """
            SELECT * FROM backtest_requests
            WHERE id = %s
            """,
            (str(backtest_id),)
        )
        return result
    except Exception as e:
        logger.error(f"Error in get_backtest_by_id: {e}")
        return None

def update_backtest_status(conn, backtest_id: UUID, status: str, error_message: Optional[str] = None) -> dict:
    """Update backtest status and error message"""
    try:
        result = execute_query_single(
            conn,
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
        conn.commit()

        logger.info(f"Successfully updated backtest status: {result}")

        # Broadcast the backtest update asynchronously
        asyncio.run(post_backtest_update(backtest_id=backtest_id))

        logger.info("Broadcast backtest update initiated.")
        return result
    except Exception as e:
        print('> error: ', e)
        # Rollback the transaction to maintain consistency
        conn.rollback()
        logger.warning(f"Error updating status for backtest {backtest_id}: {e}", exc_info=True)
        return None

def update_backtest_urls(
    conn,
    backtest_id: UUID,
    python_script_url: Optional[str] = None,
    validation_data_url: Optional[str] = None,
    full_data_url: Optional[str] = None,
    log_file_url: Optional[str] = None,
    report_url: Optional[str] = None
) -> dict:
    """Update backtest file URLs"""
    try:
        result = execute_query_single(
            conn,
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
        conn.commit()
        asyncio.run(post_backtest_update(backtest_id=backtest_id))
        return result
    except Exception as e:
        conn.rollback()
        logger.warning(f'Error updating backtest file: {e}')
