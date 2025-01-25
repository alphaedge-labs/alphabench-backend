from openai import AsyncOpenAI
import re
import json
from typing import Optional

from src.config.settings import settings
from src.utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUEST_DURATION,
    track_time
)
from src.utils.logger import get_logger
from src.infrastructure.llm.prompts import (
    # Backtest Script Prompts
    backtest_script_deepseek_system_prompt_vectorbt,
    # Strategy Title Prompts
    strategy_title_system_prompt,
    # Backtest Report Prompts
    backtest_report_system_prompt_v3
)

# client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
deepseek_client = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)

logger = get_logger(__name__)

@track_time(LLM_REQUEST_DURATION.labels(operation='title_generation'))
async def generate_strategy_title(strategy_description: str) -> str:
    """Generate a short title for the trading strategy"""
    try:
        response = await deepseek_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": strategy_title_system_prompt
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
        system_prompt = backtest_script_deepseek_system_prompt_vectorbt
        
        if extra_message:
            system_prompt = system_prompt + f"\n{extra_message}"

        logger.info(f"Generated system prompt: {system_prompt}")

        response = await deepseek_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": strategy_description}
            ],
            temperature=0.2,
            response_format={
                "type": "json_object"
            }
        )
        
        llm_response = response.choices[0].message.content
        llm_response = re.sub(r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', llm_response)

        logger.info(f'Response content: {llm_response}')

        try:
            content = json.loads(llm_response)
        except json.JSONDecodeError as e:
            print(f'JSON Decode Error: {e}')
            print(f'Problematic JSON: {llm_response}')
            return None, None
        
        logger.info(f'Response content: {content}')

        # Finding script
        script = content.get('script')
        # Fetching data columns
        data_columns = content.get('data_columns')

        return script, data_columns
    except Exception as e:
        # Log error here
        raise Exception(f"Failed to generate backtest script: {str(e)}")

async def generate_backtest_report(log_content: str) -> str:
    """Generate a markdown report from backtest logs"""
    try:
        response = await deepseek_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": backtest_report_system_prompt_v3
                },
                {
                    "role": "user",
                    "content": log_content
                }
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Log error here
        raise Exception(f"Failed to generate backtest report: {str(e)}")

async def generate_fixed_script(original_script: str, error_message: str) -> str:
    """Generate a fixed Python script based on the original script and error message"""
    try:
        system_prompt = (
            "You are a Python expert. Your task is to fix the following Python script based on the provided error message. "
            "Ensure that the new script doesn't need any other data input than original script.\n\n"
            "Original Script:\n"
            f"{original_script}\n\n"
            "Error Message:\n"
            f"{error_message}\n\n"
            "Please provide the corrected script only in response."
        )

        response = await deepseek_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                }
            ],
            max_tokens=2000,
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()

        script_match = re.search(r'```python\n(.*?)```', content, re.DOTALL)
        script = script_match.group(1).strip() if script_match else None

        return script
    except Exception as e:
        raise Exception(f"Failed to generate fixed script: {str(e)}")

async def fix_backtest_script(script: str, error_message: str) -> Optional[str]:
    """
    Attempt to fix a backtest script based on the error message.
    Returns improved script or None if unable to fix.
    """
    system_prompt = """You are an expert Python developer specializing in algorithmic trading.
    Fix the provided backtest script based on the error message. Ensure the script follows
    best practices and handles edge cases appropriately. If the error cannot be fixed or
    requires fundamental strategy changes, return None."""

    user_message = f"""
    The following backtest script failed validation with this error:
    {error_message}

    Here's the script:
    {script}

    Please provide an improved version that fixes the error, or return None if the error
    cannot be fixed without changing the core strategy."""

    response = await deepseek_client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        max_tokens=2000,
        temperature=0.2
    )

    if response and "None" not in response.choices[0].message.content:
        return response.choices[0].message.content.strip()
    return None
