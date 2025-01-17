from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.db.base import get_db
from src.schemas.subscriptions import (
    SubscriptionPlanResponse,
    UserSubscriptionResponse,
    SubscriptionCreate
)
from src.core.auth.jwt import get_current_active_user
from src.db.queries.subscriptions import (
    get_subscription_plans,
    get_user_subscription,
    create_user_subscription
)

router = APIRouter(
    prefix="/v1/subscriptions",
    tags=["subscriptions"],
    responses={
        401: {"description": "Not authenticated"},
        403: {
            "description": "Not authorized",
            "content": {
                "application/json": {
                    "example": {"detail": "Anonymous users cannot subscribe"}
                }
            }
        }
    }
)

@router.get(
    "",
    response_model=List[SubscriptionPlanResponse],
    responses={
        200: {
            "description": "List of available subscription plans",
            "content": {
                "application/json": {
                    "example": [{
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Professional",
                        "description": "Advanced backtesting with unlimited reports",
                        "price_usd": 49.99,
                        "reports_per_day": 100
                    }]
                }
            }
        }
    }
)
async def list_plans(
    db = Depends(get_db)
) -> List[SubscriptionPlanResponse]:
    """
    List all available subscription plans.
    
    Returns a list of plans with their features and pricing.
    This endpoint is publicly accessible without authentication.
    """
    with db as conn:
        return get_subscription_plans(conn)

@router.get(
    "/active",
    response_model=UserSubscriptionResponse,
    responses={
        200: {
            "description": "User's active subscription details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "plan": {
                            "name": "Professional",
                            "reports_per_day": 100
                        },
                        "end_date": "2024-12-31T23:59:59Z"
                    }
                }
            }
        },
        404: {
            "description": "No active subscription found",
            "content": {
                "application/json": {
                    "example": {"detail": "No active subscription found"}
                }
            }
        }
    }
)
async def get_active_subscription(
    current_user: dict = Depends(get_current_active_user),
    db = Depends(get_db)
) -> UserSubscriptionResponse:
    """
    Get user's active subscription.
    
    Returns details about the user's current subscription plan,
    including end date and usage limits.
    
    Returns 404 if the user has no active subscription.
    """
    subscription = get_user_subscription(db, current_user['id'])
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    return subscription

@router.post(
    "",
    response_model=UserSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Subscription created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "plan": {
                            "name": "Professional",
                            "reports_per_day": 100
                        },
                        "start_date": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid subscription request",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid plan ID"}
                }
            }
        },
        402: {
            "description": "Payment required",
            "content": {
                "application/json": {
                    "example": {"detail": "Payment processing failed"}
                }
            }
        }
    }
)
async def create_subscription(
    subscription: SubscriptionCreate,
    current_user: dict = Depends(get_current_active_user),
    db = Depends(get_db)
) -> UserSubscriptionResponse:
    """
    Create a new subscription for the current user.
    
    This endpoint:
    1. Validates the subscription plan
    2. Processes the payment
    3. Creates the subscription record
    4. Updates user's rate limits
    
    The payment_token should be obtained from the payment provider's
    frontend integration (e.g., Stripe).
    
    Anonymous users cannot create subscriptions.
    """
    if current_user['is_anonymous']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous users cannot subscribe"
        )
    
    return await create_user_subscription(
        db,
        user_id=current_user['id'],
        plan_id=subscription.plan_id,
        payment_token=subscription.payment_token
    )
