from fastapi import Depends, HTTPException, status, Request
from datetime import date
from typing import Optional

from src.db.base import get_db, execute_query_single
from src.core.auth.jwt import get_current_user
from src.config.settings import settings

async def get_user_rate_limit(user_id: str, conn) -> int:
    """Get user's daily rate limit based on subscription"""
    # Check if user has active subscription
    subscription = execute_query_single(
        conn,
        """
        SELECT sp.reports_per_day
        FROM user_subscriptions us
        JOIN subscription_plans sp ON us.plan_id = sp.id
        WHERE us.user_id = %s
        AND us.is_active = true
        AND us.start_date <= CURRENT_TIMESTAMP
        AND us.end_date >= CURRENT_TIMESTAMP
        """,
        (user_id,)
    )
    
    if subscription:
        return subscription['reports_per_day']
    return settings.AUTHENTICATED_DAILY_LIMIT

async def check_user_rate_limit(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Check if user has exceeded their daily rate limit"""
    with get_db() as conn:
        # Get today's report count
        daily_count = execute_query_single(
            conn,
            """
            SELECT count FROM daily_report_counts
            WHERE user_id = %s AND date = %s
            """,
            (current_user['id'], date.today())
        )
        
        # Get user's rate limit
        rate_limit = (
            settings.ANONYMOUS_DAILY_LIMIT 
            if current_user['is_anonymous']
            else await get_user_rate_limit(current_user['id'], conn)
        )
        
        # Check if user has exceeded limit
        current_count = daily_count['count'] if daily_count else 0
        if current_count >= rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily report limit of {rate_limit} exceeded"
            )
        
        # Update or create daily count
        if not daily_count:
            execute_query_single(
                conn,
                """
                INSERT INTO daily_report_counts (user_id, date, count)
                VALUES (%s, %s, 1)
                """,
                (current_user['id'], date.today())
            )
        else:
            execute_query_single(
                conn,
                """
                UPDATE daily_report_counts
                SET count = count + 1
                WHERE user_id = %s AND date = %s
                """,
                (current_user['id'], date.today())
            )
        conn.commit()
        
        return current_user

async def identify_anonymous_user(request: Request) -> dict:
    """Create or get anonymous user based on IP and MAC address"""
    ip_address = request.client.host

    # Note: MAC address would typically come from request headers or other means
    mac_address = request.headers.get('X-MAC-Address', 'unknown')
    
    with get_db() as conn:
        user = execute_query_single(
            conn,
            """
            SELECT * FROM users
            WHERE ip_address = %s AND mac_address = %s AND is_anonymous = true
            """,
            (ip_address, mac_address)
        )
        
        if not user:
            user = execute_query_single(
                conn,
                """
                INSERT INTO users (ip_address, mac_address, is_anonymous)
                VALUES (%s, %s, true)
                RETURNING *
                """,
                (ip_address, mac_address)
            )
            conn.commit()
            
        return user
