from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta

from src.core.auth.google import GoogleOAuth
from src.core.auth.jwt import create_access_token, get_current_user
from src.db.base import get_db
from src.schemas.auth import Token, UserResponse, GoogleAuthRequest
from src.config.settings import settings

router = APIRouter(
    prefix="/v1/auth",
    tags=["authentication"],
    responses={
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid authentication credentials"}
                }
            }
        }
    }
)

@router.post(
    "/google",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully authenticated with Google",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        400: {
            "description": "Invalid Google OAuth code",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid authorization code"}
                }
            }
        }
    }
)
async def google_auth(
    auth_request: GoogleAuthRequest,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Token:
    """
    Authenticate user with Google OAuth.
    
    This endpoint expects an authorization code obtained from the Google OAuth flow.
    It will:
    1. Validate the code with Google
    2. Create or update user record
    3. Generate a JWT access token
    
    The returned token should be included in subsequent requests in the
    Authorization header as: `Bearer <token>`
    """
    try:
        user, is_new_user = await GoogleOAuth.authenticate_user(
            auth_request.code,
            current_user.id,
            auth_request.redirect_uri,
            db
        )
        
        access_token = create_access_token(
            data={"sub": user['id']},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return Token(access_token=access_token, token_type="bearer")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
