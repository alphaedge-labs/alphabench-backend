from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.db.base import get_db
from src.schemas.reports import ReportResponse
from src.api.dependencies import get_current_user
from src.db.queries.backtests import get_backtest_by_id, get_user_backtests

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    responses={
        401: {"description": "Not authenticated"},
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {"detail": "Daily report limit exceeded"}
                }
            }
        }
    }
)

@router.get(
    "",
    response_model=List[ReportResponse],
    responses={
        200: {
            "description": "List of generated reports",
            "content": {
                "application/json": {
                    "example": [{
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "strategy_title": "Golden Cross Strategy",
                        "report_url": "https://s3.amazonaws.com/reports/123..."
                    }]
                }
            }
        }
    }
)
async def list_reports(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> List[ReportResponse]:
    """
    List all generated reports for the current user.
    
    Returns only backtest requests that have completed report generation.
    Reports are ordered by creation date (newest first).
    """
    backtests = get_user_backtests(db, current_user['id'])
    return [
        backtest for backtest in backtests 
        if backtest['generated_report']
    ]

@router.get(
    "/{backtest_id}",
    response_model=ReportResponse,
    responses={
        200: {
            "description": "Report details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "strategy_title": "Golden Cross Strategy",
                        "report_url": "https://s3.amazonaws.com/reports/123..."
                    }
                }
            }
        },
        404: {
            "description": "Report not found or not yet generated",
            "content": {
                "application/json": {
                    "example": {"detail": "Report not found"}
                }
            }
        }
    }
)
async def get_report(
    backtest_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> ReportResponse:
    """
    Get a specific report by backtest ID.
    
    Returns 404 if:
    - The backtest request doesn't exist
    - The backtest belongs to another user
    - The report hasn't been generated yet
    """
    backtest = get_backtest_by_id(db, backtest_id)
    if not backtest or backtest['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    if not backtest['generated_report']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not yet generated"
        )
    return backtest
