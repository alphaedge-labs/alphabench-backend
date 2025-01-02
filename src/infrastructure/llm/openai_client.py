from openai import AsyncOpenAI
from typing import Optional

from src.config.settings import settings
from src.utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUEST_DURATION,
    track_time
)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

@track_time(LLM_REQUEST_DURATION.labels(operation='title_generation'))
async def generate_strategy_title(strategy_description: str) -> str:
    """Generate a short title for the trading strategy"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a trading strategy expert. Generate a short, concise title (max 50 characters) for the given trading strategy description."
                },
                {
                    "role": "user",
                    "content": strategy_description
                }
            ],
            max_tokens=50,
            temperature=0.7
        )
        LLM_REQUEST_COUNT.labels(
            operation='title_generation',
            status='success'
        ).inc()
        return response.choices[0].message.content.strip()
    except Exception as e:
        LLM_REQUEST_COUNT.labels(
            operation='title_generation',
            status='error'
        ).inc()
        # Log error here
        return "Custom Trading Strategy"  # Fallback title

async def generate_backtest_script(strategy_description: str) -> tuple[str, list[str]]:
    """Generate Python script and required data points for the strategy"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a Python trading strategy expert. Generate a detailed backtesting script with comprehensive logging for the given strategy description. 
                    The script should:
                    1. Accept a CSV file path as --data argument
                    2. Include detailed logging of entry/exit points, reasons, and performance metrics
                    3. Return a list of required data points
                    Format: Return both the Python script and a list of required data columns."""
                },
                {
                    "role": "user",
                    "content": strategy_description
                }
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        
        # Parse response to separate script and data points
        # Implementation depends on how we structure the LLM's response
        script = "# Generated script\n" + content  # Placeholder
        data_points = ["close", "volume"]  # Placeholder
        
        return script, data_points
    except Exception as e:
        # Log error here
        raise Exception(f"Failed to generate backtest script: {str(e)}")

async def generate_backtest_report(log_content: str) -> str:
    """Generate a markdown report from backtest logs"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a trading strategy analyst. Generate a detailed markdown report from the backtest logs.
                    The report should include:
                    1. Strategy Performance Summary
                    2. Key Metrics (Returns, Sharpe Ratio, etc.)
                    3. Entry/Exit Analysis
                    4. Risk Analysis
                    5. Recommendations for Improvement
                    Format the report in clean, well-structured markdown."""
                },
                {
                    "role": "user",
                    "content": log_content
                }
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Log error here
        raise Exception(f"Failed to generate backtest report: {str(e)}")
