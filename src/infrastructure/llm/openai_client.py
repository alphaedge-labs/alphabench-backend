from openai import AsyncOpenAI
import re
import json

from src.config.settings import settings
from src.utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUEST_DURATION,
    track_time
)
from src.utils.logger import get_logger
from src.infrastructure.llm.prompts import (
    # Backtest Script Prompts
    backtest_script_system_prompt_vectorbt,
    # Strategy Title Prompts
    strategy_title_system_prompt,
    # Backtest Report Prompts
    backtest_report_system_prompt_v3
)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
logger = get_logger(__name__)

@track_time(LLM_REQUEST_DURATION.labels(operation='title_generation'))
async def generate_strategy_title(strategy_description: str) -> str:
    """Generate a short title for the trading strategy"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
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
        system_prompt = backtest_script_system_prompt_vectorbt
        
        if extra_message:
            system_prompt = system_prompt + f"\n{extra_message}"

        logger.info(f"Generated system prompt: {system_prompt}")

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": strategy_description}
            ],
            max_tokens=2000,
            temperature=0.2,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "backtest_script_response",  # Name of the schema
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "script": {"type": "string"},  # Python script as a string
                            "data_columns": {  # List of required data columns
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["script", "data_columns"],
                        "additionalProperties": False  # Enforce strict schema compliance
                    }
                }
            }
        )
        
        llm_response = response.choices[0].message.content

        logger.info(f'Response content: {llm_response}')

        content = json.loads(llm_response)

        logger.info(f'Response content: {content}')

        # Finding script
        # script_match = re.search(r'```python\n(.*?)```', content['script'], re.DOTALL)
        # script = script_match.group(1).strip() if script_match else None
        script = content['script']

        # Fetching data columns
        data_columns = content['data_columns']

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
                    "content": backtest_report_system_prompt_v3
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

        response = await client.chat.completions.create(
            model="gpt-4o",
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
