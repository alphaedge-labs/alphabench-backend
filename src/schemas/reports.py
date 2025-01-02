from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ReportResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique identifier for the backtest/report",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    strategy_title: str = Field(
        ...,
        description="Auto-generated title summarizing the strategy",
        example="Golden Cross MA(50,200) Strategy"
    )
    status: str = Field(
        ...,
        description="Current status of the report generation",
        example="completed"
    )
    report_url: Optional[str] = Field(
        None,
        description="S3 URL of the generated markdown report",
        example="https://s3.amazonaws.com/reports/123e4567-e89b-12d3-a456-426614174000/report.md"
    )
    created_at: datetime = Field(
        ...,
        description="When the backtest request was created",
        example="2024-01-01T00:00:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="When the report was last updated",
        example="2024-01-01T00:10:00Z"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "strategy_title": "Golden Cross MA(50,200) Strategy",
                "status": "completed",
                "report_url": "https://s3.amazonaws.com/reports/123e4567-e89b-12d3-a456-426614174000/report.md",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:10:00Z"
            }
        }
