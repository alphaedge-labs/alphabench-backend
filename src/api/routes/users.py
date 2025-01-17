from fastapi import APIRouter, Depends

from src.core.auth.jwt import get_current_active_user
from src.schemas.auth import UserResponse
from src.db.queries.subscriptions import get_subscription_by_user_id
from src.db.base import get_db

router = APIRouter(
    prefix="/v1/users",
    tags=["users"],
    responses={
        401: {
            "description": "User api failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid authentication credentials"}
                }
            }
        }
    }
)

@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "is_anonymous": False,
                        "subscription_status": "active",
                        "subscription_id": "sub_123456",
                        "subscription_end_date": "2024-12-31T23:59:59Z",
                        "subscription_plan_name": "Professional",
                        "subscription_plan_id": "plan_123456"
                    }
                }
            }
        }
    }
)
async def get_current_user(
    current_user: dict = Depends(get_current_active_user),
    db = Depends(get_db)
) -> UserResponse:
    """
    Get current authenticated user's information.
    
    This endpoint requires a valid JWT token in the Authorization header.
    It returns the user's profile information, including whether they are
    an anonymous user or authenticated via Google, along with their
    current subscription status if any.
    """
    with db as conn:
        # Get user's active subscription
        subscription = get_subscription_by_user_id(conn, current_user['id'])

        # Combine user and subscription data
        user_data = {
            **current_user,
            "subscription_id": subscription['subscription_id'] if subscription else None,
            "subscription_status": subscription['subscription_status'] if subscription else None,
            "subscription_end_date": subscription['subscription_end_date'] if subscription else None,
            "subscription_plan_name": subscription['subscription_plan_name'] if subscription else None,
            "subscription_plan_id": subscription['subscription_plan_id'] if subscription else None
        }

        return UserResponse(**user_data)
