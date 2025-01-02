from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class BacktestCreate(BaseModel):
    instrument_symbol: str = Field(
        ..., 
        min_length=1, 
        max_length=20,
        description="Trading instrument symbol (e.g., 'AAPL', 'BTC-USD')",
        example="AAPL"
    )
    from_date: date = Field(
        ...,
        description="Start date for backtesting period",
        example="2023-01-01"
    )
    to_date: date = Field(
        ...,
        description="End date for backtesting period",
        example="2023-12-31"
    )
    strategy_description: str = Field(
        ..., 
        min_length=10,
        description="""
        Natural language description of the trading strategy.
        Be as detailed as possible about entry/exit conditions, position sizing, etc.
        """,
        example="Buy when the 50-day moving average crosses above the 200-day moving average. "
                "Sell when it crosses below. Use 1% of portfolio per trade."
    )

class BacktestRequest(BacktestCreate):
    id: UUID = Field(
        ...,
        description="Unique identifier for the backtest request"
    )
    user_id: UUID = Field(
        ...,
        description="ID of the user who created the backtest"
    )
    strategy_title: Optional[str] = Field(
        None,
        description="Auto-generated title summarizing the strategy",
        example="Golden Cross MA(50,200) Strategy"
    )
    python_script_url: Optional[str] = Field(
        None,
        description="S3 URL of the generated Python script"
    )
    validation_data_url: Optional[str] = Field(
        None,
        description="S3 URL of the validation dataset"
    )
    full_data_url: Optional[str] = Field(
        None,
        description="S3 URL of the full dataset"
    )
    log_file_url: Optional[str] = Field(
        None,
        description="S3 URL of the execution log file"
    )
    report_url: Optional[str] = Field(
        None,
        description="S3 URL of the generated report"
    )
    ready_for_report: bool = Field(
        False,
        description="Indicates if backtest execution is complete and ready for report generation"
    )
    generated_report: bool = Field(
        False,
        description="Indicates if the final report has been generated"
    )
    status: str = Field(
        "pending",
        description="""
        Current status of the backtest request. Possible values:
        - pending: Initial state
        - generating_script: LLM is generating the Python script
        - validating: Running script with validation dataset
        - validation_failed: Script failed validation
        - executing: Running full backtest
        - execution_failed: Full backtest failed
        - generating_report: Creating final report
        - completed: Process complete
        - failed: Process failed
        """
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if any step failed"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the request was created"
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the request was last updated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "instrument_symbol": "AAPL",
                "from_date": "2023-01-01",
                "to_date": "2023-12-31",
                "strategy_description": "Buy when the 50-day moving average crosses above the 200-day moving average...",
                "strategy_title": "Golden Cross MA(50,200) Strategy",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:10:00Z"
            }
        }

class BacktestResponse(BacktestRequest):
    pass
