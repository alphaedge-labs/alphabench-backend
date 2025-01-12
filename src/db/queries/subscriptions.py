from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from src.db.base import execute_query, execute_query_single

def get_subscription_plans(conn) -> List[dict]:
    """Get all available subscription plans"""
    return execute_query(
        conn,
        """
        SELECT 
            id, name, description, price_usd, reports_per_day,
            created_at
        FROM subscription_plans
        ORDER BY price_usd ASC
        """
    )

def get_user_subscription(db, user_id: UUID) -> Optional[dict]:
    """Get user's active subscription"""
    return execute_query_single(
        db,
        """
        SELECT 
            us.id,
            us.start_date,
            us.end_date,
            sp.name as plan_name,
            sp.reports_per_day,
            sp.price_usd
        FROM user_subscriptions us
        JOIN subscription_plans sp ON us.plan_id = sp.id
        WHERE us.user_id = %s
        AND us.end_date > CURRENT_TIMESTAMP
        AND us.status = 'active'
        ORDER BY us.end_date DESC
        LIMIT 1
        """,
        (user_id,)
    )

async def create_user_subscription(
    db,
    user_id: UUID,
    plan_id: UUID,
    payment_token: str
) -> dict:
    """Create a new subscription for a user"""
    # First, verify the plan exists and is active
    plan = execute_query_single(
        db,
        """
        SELECT id, price_usd
        FROM subscription_plans
        WHERE id = %s AND is_active = true
        """,
        (plan_id,)
    )
    
    if not plan:
        raise ValueError("Invalid or inactive subscription plan")

    # Start a transaction
    with db.cursor() as cur:
        try:
            # Process payment (placeholder - implement actual payment processing)
            # TODO: Integrate with payment provider using payment_token
            
            # Calculate subscription dates
            now = datetime.now(timezone.utc)
            end_date = datetime(
                now.year + 1 if now.month == 12 else now.year,
                1 if now.month == 12 else now.month + 1,
                1,
                tzinfo=timezone.utc
            )

            # Deactivate any existing active subscriptions
            cur.execute(
                """
                UPDATE user_subscriptions
                SET status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                AND status = 'active'
                AND end_date > CURRENT_TIMESTAMP
                """,
                (user_id,)
            )

            # Create new subscription
            cur.execute(
                """
                INSERT INTO user_subscriptions (
                    user_id, plan_id, start_date, end_date,
                    status, payment_token
                )
                VALUES (%s, %s, CURRENT_TIMESTAMP, %s, 'active', %s)
                RETURNING id
                """,
                (user_id, plan_id, end_date, payment_token)
            )
            subscription_id = cur.fetchone()['id']

            # Get full subscription details
            cur.execute(
                """
                SELECT 
                    us.id,
                    us.start_date,
                    us.end_date,
                    sp.name as plan_name,
                    sp.reports_per_day
                FROM user_subscriptions us
                JOIN subscription_plans sp ON us.plan_id = sp.id
                WHERE us.id = %s
                """,
                (subscription_id,)
            )
            subscription = cur.fetchone()

            db.commit()
            return subscription

        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create subscription: {str(e)}")

def get_subscription_usage(db, user_id: UUID) -> dict:
    """Get user's subscription usage for the current day"""
    return execute_query_single(
        db,
        """
        SELECT COUNT(*) as daily_count
        FROM backtest_requests
        WHERE user_id = %s
        AND DATE(created_at) = CURRENT_DATE
        """,
        (user_id,)
    )
