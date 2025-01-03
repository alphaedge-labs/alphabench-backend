# src/api/routes/backtests.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from src.db.base import get_db
from src.schemas.backtests import (
    BacktestRequest,
    BacktestResponse,
    BacktestCreate
)
from src.api.dependencies import check_user_rate_limit
from src.tasks.script_generation import generate_backtest_script_task as generate_backtest_script

from src.db.queries.backtests import (
    create_backtest_request,
    get_user_backtests,
    get_backtest_by_id
)
from src.infrastructure.llm.openai_client import generate_strategy_title

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
    strategy_title = await generate_strategy_title(backtest.strategy_description)
    
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

@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: UUID,
    current_user: dict = Depends(check_user_rate_limit),
    db = Depends(get_db)
) -> BacktestResponse:
    """
    Get specific backtest details
    """

    print('> backtest_id: ', backtest_id)
    print('> current_user: ', current_user['id'])

    with db as conn:
        backtest = get_backtest_by_id(conn=conn, backtest_id=backtest_id)
        print('> backtest returned: ', backtest)

    if not backtest or backtest['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )
    
    return BacktestResponse(**backtest)