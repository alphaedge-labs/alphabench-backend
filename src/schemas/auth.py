from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class Token(BaseModel):
    access_token: str = Field(
        ...,
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        "bearer",
        description="Token type (always 'bearer')",
        example="bearer"
    )

class GoogleAuthRequest(BaseModel):
    code: str = Field(
        ...,
        description="Authorization code from Google OAuth flow",
        example="4/0AfJohXnLW7..."
    )
    redirect_uri: str = Field(
        ...,
        description="OAuth redirect URI that was used in the authorization request",
        example="https://app.alphabench.in/auth/callback"
    )

class UserResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique identifier for the user"
    )
    name: Optional[str] = Field(
        None,
        description="User's name (if authenticated via Google)",
        example="John Doe"
    )
    picture_url: Optional[str] = Field(
        None,
        description="User's picture URL (if authenticated via Google)",
        example="https://lh3.googleusercontent.com/a/ACg8ocJrY-..."
    )
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address (if authenticated via Google)",
        example="user@example.com"
    )
    google_id: Optional[str] = Field(
        None,
        description="User's Google ID (if authenticated via Google)"
    )
    is_anonymous: bool = Field(
        ...,
        description="Whether this is an anonymous user",
        example=False
    )
    subscription_status: Optional[str] = Field(
        ...,
        description="Subscription status",
        example="active"
    )
    subscription_id: Optional[str] = Field(
        ...,
        description="Subscription ID",
        example="sub_1234567890"
    )
    subscription_end_date: Optional[datetime] = Field(
        ...,
        description="Subscription end date",
        example="2024-01-01T00:00:00Z"
    )
    subscription_plan_name: Optional[str] = Field(
        ...,
        description="Subscription plan name",
        example="Basic"
    )
    subscription_plan_id: Optional[str] = Field(
        ...,
        description="Subscription plan ID",
        example="plan_1234567890"
    )
    created_at: datetime = Field(
        ...,
        description="When the user account was created",
        example="2024-01-01T00:00:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="When the user account was last updated",
        example="2024-01-01T00:00:00Z"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "google_id": "109876543210987654321",
                "is_anonymous": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
