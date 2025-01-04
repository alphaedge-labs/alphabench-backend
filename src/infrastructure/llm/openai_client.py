from openai import AsyncOpenAI
from logging import getLogger
import re

from src.config.settings import settings
from src.utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUEST_DURATION,
    track_time
)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
logger = getLogger()

@track_time(LLM_REQUEST_DURATION.labels(operation='title_generation'))
async def generate_strategy_title(strategy_description: str) -> str:
    """Generate a short title for the trading strategy"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a trading strategy expert. Generate a short, concise title (max 50 characters) for the given trading strategy description. Do not enclose your response with quotation marks."
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

async def generate_backtest_script(strategy_description: str, extra_message: str) -> tuple[str, list[str]]:
    """Generate Python script and required data points for the strategy"""
    try:
        system_prompt = (
            "You are a Python trading strategy expert. Generate a detailed backtesting script with comprehensive logging for the given strategy description in prompt."
            "For each prompt, you must:\n"
            "1. Generate a Python script that accepts a CSV file as an argument (e.g., `python script.py -d data.csv`).\n"
            "2. Include detailed logging of entry/exit points, reasons, and performance metrics such that backtesting report can be generated from these logs\n"
            "3. REMEMBER! Add a sentence at the end of your response which specifies the required data columns in data.csv explicitly in this format: 'Required data columns: column1, column2, column3'\n"
            "Do not generate any more data than I have asked you to generate."
        )

        if extra_message:
            system_prompt = system_prompt + f"\n{extra_message}"

        logger.info(f"Generated system prompt: {system_prompt}")

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": strategy_description
                }
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()
        
        print('content: ', content)

        # Parse response to separate script and data points
        # Use regular expressions to extract the script and data columns
        script_match = re.search(r'```python\n(.*?)```', content, re.DOTALL)
        data_columns_match = re.search(r'(Required data columns:.*)', content, re.DOTALL)
        if data_columns_match:
            data_columns = [col.strip() for col in data_columns_match.group(1).replace("Required data columns:", "").split(',')]
        else:
            data_columns = None

        script = script_match.group(1).strip() if script_match else None
        return script, data_columns
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
