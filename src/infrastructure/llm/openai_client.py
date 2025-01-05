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
            "You are a Python trading strategy expert. Your task is to generate a detailed backtesting script "
            "that adheres to the provided trading strategy description. Follow these strict guidelines:\n"
            "\n"
            "1. **Output Format**:\n"
            "   - Your response should only contain the generated Python script enclosed in triple backticks (` ```python ... ``` `).\n"
            "   - After the script, provide the required data columns explicitly in this format: 'Required data columns: column1, column2, ...'.\n"
            "   - Do not include any additional explanations, commentary, or extraneous text outside the specified format.\n"
            "\n"
            "2. **Script Requirements**:\n"
            "   - The script must accept a CSV file as input (specified via a command-line argument, e.g., `-d data.csv`).\n"
            "   - The script must also accept log file path as input (specified via a command-line argument, e.g., `--log backtest.log`).\n"
            "   - Validate the input file for the required data columns and handle missing or invalid data gracefully.\n"
            "   - Include robust error handling with detailed logging for debugging purposes.\n"
            "   - The script must calculate moving averages, generate buy/sell signals, and backtest the strategy.\n"
            "   - Use only widely supported Python libraries such as pandas, numpy, argparse, and logging.\n"
            "   - Make sure that all the functions have all required arguments passed to them (for eg. for moving average strategies generate_signals(df, short_window, long_window)).\n"
            "   - The script must have detailed logs on every sensible steps of the code such that a detailed strategy report can be generated in markdown format from this log file for the requested strategy and data.\n"
            "\n"
            "3. **Code Quality**:\n"
            "   - Ensure the script is modular, production-ready, and free from syntax or runtime errors.\n"
            "   - Test your response against common scenarios to ensure accuracy and reliability.\n"
            "\n"
            "4. **Data Columns**:\n"
            "   - At the end of your response, explicitly list the required columns for the input CSV file in the specified format."
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
            model="gpt-4",
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
