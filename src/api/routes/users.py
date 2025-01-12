from fastapi import APIRouter, Depends

from src.core.auth.jwt import get_current_active_user
from src.schemas.auth import UserResponse

router = APIRouter(
    prefix="/api/v1/users",
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
                        "is_anonymous": False
                    }
                }
            }
        }
    }
)
async def get_current_user(
    current_user: dict = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user's information.
    
    This endpoint requires a valid JWT token in the Authorization header.
    It returns the user's profile information, including whether they are
    an anonymous user or authenticated via Google.
    """
    return UserResponse(**current_user)
