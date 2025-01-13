# src/api/routes/backtests.py
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID
from pydantic import BaseModel
import httpx

from src.db.base import get_db
from src.schemas.backtests import (
    BacktestResponse,
    BacktestCreate,
    BacktestUpdate,
    GroupedBacktestsResponse
)
from src.api.dependencies import check_user_rate_limit
from src.tasks.script_generation import generate_backtest_script_task as generate_backtest_script

from src.db.queries.backtests import (
    create_backtest_request,
    get_user_backtests,
    get_backtest_by_id,
    get_grouped_backtests,
    get_grouped_backtests_search
)
from src.infrastructure.llm.openai_client import generate_strategy_title
from src.infrastructure.llm.localllm_client import CustomLLMClient

from src.api.services.websocket import manager
from src.core.auth.jwt import get_current_user


router = APIRouter(prefix="/api/v1/backtests", tags=["backtests"])

@router.post(
    "", 
    response_model=BacktestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Backtest request created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pending",
                        "strategy_title": "Golden Cross Strategy"
                    }
                }
            }
        },
        429: {
            "description": "Daily rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Daily report limit of 5 exceeded"
                    }
                }
            }
        }
    }
)
async def create_backtest(
    backtest: BacktestCreate,
    current_user: dict = Depends(check_user_rate_limit),
    db = Depends(get_db)
) -> BacktestResponse:
    """
    Create a new backtest request.
    
    The request goes through the following pipeline:
    1. Strategy title generation using LLM
    2. Python script generation
    3. Script validation
    4. Full backtest execution
    5. Report generation
    
    Rate limits apply based on user type:
    - Anonymous: 3/day
    - Authenticated: 5/day
    - Subscribed: n/day (based on plan)
    """
    # Generate strategy title using LLM
    custom_llm = CustomLLMClient()

    strategy_title = await generate_strategy_title(backtest.strategy_description)
    
    # Sanitize strategy title by removing any leading or trailing whitespace
    strategy_title = strategy_title.strip('"')

    # Create backtest request in database
    backtest_dict = backtest.model_dump()
    backtest_dict['strategy_title'] = strategy_title
    
    with db as conn:  # Use the connection within a context manager
        backtest_db = create_backtest_request(
            conn=conn,
            user_id=current_user['id'],
            backtest=backtest_dict
        )
    
    
    # Queue backtest for processing
    generate_backtest_script.delay(backtest_id=backtest_db['id'])
    
    return BacktestResponse(**backtest_db)

@router.get(
    "", 
    response_model=List[BacktestResponse],
    responses={
        200: {
            "description": "List of user's backtest requests",
            "content": {
                "application/json": {
                    "example": [{
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "completed",
                        "strategy_title": "Golden Cross Strategy"
                    }]
                }
            }
        }
    }
)
async def list_backtests(
    current_user: dict = Depends(check_user_rate_limit),
    db = Depends(get_db)
) -> List[BacktestResponse]:
    """
    List all backtest requests for the current user.
    
    Results are ordered by creation date (newest first).
    """
    with db as conn:
        backtests = get_user_backtests(conn, current_user['id'])
        return [BacktestResponse(**backtest) for backtest in backtests]

@router.get(
    "/past",
    response_model=GroupedBacktestsResponse,
    responses={
        200: {
            "description": "Past backtests grouped by time periods",
            "content": {
                "application/json": {
                    "example": {
                        "thisWeek": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000", 
                                "name": "Moving Average Strategy #1", 
                                "date": "2024-03-20"
                            }
                        ],
                        "lastMonth": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174001", 
                                "name": "RSI Strategy #1", 
                                "date": "2024-02-28"
                            }
                        ],
                        "older": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174002", 
                                "name": "RSI Strategy #2", 
                                "date": "2024-01-15"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_past_backtests(
    current_user: dict = Depends(check_user_rate_limit),
    db = Depends(get_db)
) -> GroupedBacktestsResponse:
    """
    Get past backtests for the current user, grouped by time periods:
    - thisWeek: Backtests from the last 7 days
    - lastMonth: Backtests from the last 30 days (excluding thisWeek)
    - older: All backtests older than 30 days
    """
    with db as conn:
        result = get_grouped_backtests(conn, current_user['id'])
        return GroupedBacktestsResponse(**result['result'])

@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: UUID,
    current_user: dict = Depends(check_user_rate_limit),
    db = Depends(get_db)
) -> BacktestResponse:
    """
    Get specific backtest details
    """
    with db as conn:
        backtest = get_backtest_by_id(conn=conn, backtest_id=backtest_id)

    if not backtest or backtest['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    return BacktestResponse(**backtest)

@router.post("/broadcast/{backtest_id}", status_code=status.HTTP_200_OK)
async def broadcast_backtest(
    backtest_id: UUID,
    db = Depends(get_db)
):
    """
    Broadcast backtest update to the user.
    """
    with db as conn:
        backtest_update = get_backtest_by_id(conn, backtest_id=backtest_id)

        if not backtest_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest not found"
            )

        data = {
            "event": "backtest.update",
            "data": BacktestUpdate(**backtest_update).model_dump()
        }

        await manager.broadcast(backtest_update["user_id"], json.dumps(data))
        
        return {"message": "Backtest update broadcasted successfully"}

@router.get("/{backtest_id}/report", response_model=str, responses={
    200: {
        "description": "Markdown report content",
        "content": {
            "text/plain": {
                "example": "# Strategy Performance Report\n\n## Summary\n..."
            }
        }
    },
    404: {
        "description": "Report not found",
        "content": {
            "application/json": {
                "example": {"detail": "Report not found"}
            }
        }
    }
})
async def get_backtest_report(
    backtest_id: UUID,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> str:
    """
    Get the markdown report for a specific backtest.
    Only accessible by the user who generated the backtest.
    """
    with db as conn:
        backtest = get_backtest_by_id(conn=conn, backtest_id=backtest_id)

    if not backtest or backtest['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    if not backtest.get('report_url'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not yet generated"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(backtest['report_url'])
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to fetch report"
        )
    
@router.get(
    "/past/search",
    response_model=GroupedBacktestsResponse,
    responses={
        200: {
            "description": "Search results for past backtests grouped by time periods",
            "content": {
                "application/json": {
                    "example": {
                        "thisWeek": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "name": "Moving Average Strategy #1",
                                "date": "2024-03-20"
                            }
                        ],
                        "lastMonth": [],
                        "older": []
                    }
                }
            }
        }
    }
)
async def search_past_backtests(
    q: str = Query(..., description="Search term to filter backtests"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
) -> GroupedBacktestsResponse:
    """
    Search past backtests for the current user and return results grouped by time periods.
    Searches through strategy titles, descriptions, and instrument symbols.
    Results are grouped into:
    - thisWeek: Matching backtests from this week
    - lastMonth: Matching backtests from this month but before this week
    - older: Matching backtests before the current month
    """
    with db as conn:
        result = get_grouped_backtests_search(conn, current_user['id'], q)
        return GroupedBacktestsResponse(**result['result'])