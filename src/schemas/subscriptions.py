from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

class SubscriptionPlanResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique identifier for the subscription plan"
    )
    name: str = Field(
        ...,
        description="Name of the subscription plan",
        example="Professional"
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of the plan features",
        example="Advanced backtesting with unlimited reports per day"
    )
    price_usd: Decimal = Field(
        ...,
        description="Monthly price in USD",
        example=49.99,
        ge=0
    )
    reports_per_day: int = Field(
        ...,
        description="Number of reports allowed per day",
        example=100,
        gt=0
    )
    created_at: datetime = Field(
        ...,
        description="When the plan was created",
        example="2024-01-01T00:00:00Z"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Professional",
                "description": "Advanced backtesting with unlimited reports per day",
                "price_usd": 49.99,
                "reports_per_day": 100,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }

class UserSubscriptionResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique identifier for the subscription"
    )
    user_id: UUID = Field(
        ...,
        description="ID of the subscribed user"
    )
    plan_id: UUID = Field(
        ...,
        description="ID of the subscription plan"
    )
    start_date: datetime = Field(
        ...,
        description="When the subscription starts",
        example="2024-01-01T00:00:00Z"
    )
    end_date: datetime = Field(
        ...,
        description="When the subscription ends",
        example="2024-12-31T23:59:59Z"
    )
    is_active: bool = Field(
        ...,
        description="Whether the subscription is currently active",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="When the subscription was created"
    )
    updated_at: datetime = Field(
        ...,
        description="When the subscription was last updated"
    )
    plan: SubscriptionPlanResponse = Field(
        ...,
        description="Details of the subscribed plan"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "plan_id": "123e4567-e89b-12d3-a456-426614174002",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "plan": {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Professional",
                    "price_usd": 49.99,
                    "reports_per_day": 100
                }
            }
        }

class SubscriptionCreate(BaseModel):
    plan_id: UUID = Field(
        ...,
        description="ID of the subscription plan to purchase"
    )
    payment_token: str = Field(
        ...,
        description="Payment provider token for processing payment",
        example="tok_visa_123"
    )
