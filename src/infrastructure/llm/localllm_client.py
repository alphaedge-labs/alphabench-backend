import httpx
from logging import getLogger
from src.utils.metrics import (
    LLM_REQUEST_COUNT,
    LLM_REQUEST_DURATION,
    track_time
)
from src.config.settings import settings
from src.infrastructure.llm.prompts import (
    backtest_script_system_prompt, 
    strategy_title_system_prompt,
    backtest_report_system_prompt_v3
)

logger = getLogger()

class CustomLLMClient:
    def __init__(self, base_url: str=settings.LOCAL_LLM_SERVER_URL, model_name: str=settings.LOCAL_LLM_MODEL_NAME):
        self.base_url = base_url
        self.model_name = model_name

        logger.info(f"Accessing local llm at base_url: {self.base_url}")
        logger.info(f"Accessing local llm model_name: {self.model_name}")

    async def _send_request(self, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Request failed: {exc}")
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error: {exc.response.status_code} - {exc.response.text}")
            raise

    @track_time(LLM_REQUEST_DURATION.labels(operation='title_generation'))
    async def generate_strategy_title(self, strategy_description: str) -> str:
        """Generate a short title for the trading strategy."""
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": strategy_title_system_prompt
                },
                {
                    "role": "user",
                    "content": strategy_description
                }
            ],
            "max_tokens": 50,
            "temperature": 0.7,
        }

        try:
            response = await self._send_request(payload)
            LLM_REQUEST_COUNT.labels(
                operation='title_generation',
                status='success'
            ).inc()
            return response['choices'][0]['message']['content'].strip()
        except Exception:
            LLM_REQUEST_COUNT.labels(
                operation='title_generation',
                status='error'
            ).inc()
            return "Custom Trading Strategy"  # Fallback title

    async def generate_backtest_script(self, strategy_description: str, extra_message: str) -> tuple[str, list[str]]:
        """Generate Python script and required data points for the strategy."""

        system_prompt = backtest_script_system_prompt

        if extra_message:
            system_prompt += f"\n{extra_message}"

        logger.info(f'Using system_prompt: {system_prompt}')

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": strategy_description},
            ],
            "max_tokens": 2000,
            "temperature": 0.8
        }

        try:
            response = await self._send_request(payload)
            content = response['choices'][0]['message']['content']

            logger.info(f'> content: {content}')

            # Parse the script and required data columns
            import re
            script_match = re.search(r'```python\n(.*?)```', content, re.DOTALL)
            script = script_match.group(1).strip() if script_match else None

            data_columns_match = re.search(r'(Required data columns:.*)', content, re.DOTALL)
            if data_columns_match:
                data_columns = [col.strip() for col in data_columns_match.group(1).replace("Required data columns:", "").split(',')]
            else:
                data_columns = None


            return script, data_columns
        except Exception as e:
            logger.error(f"Error generating backtest script: {e}")
            raise

    async def generate_backtest_report(self, log_content: str) -> str:
        """Generate a markdown report from backtest logs."""
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": backtest_report_system_prompt_v3
                },
                {"role": "user", "content": log_content},
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        }

        try:
            response = await self._send_request(payload)
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.error(f"Error generating backtest report: {e}")
            raise

    async def generate_fixed_script(self, original_script: str, error_message: str) -> str:
        """Generate a fixed Python script based on the original script and error message."""
        system_prompt = (
            "You are a Python expert. Your task is to fix the following Python script based on the provided error message. "
            "Ensure that the new script doesn't need any other data input than original script.\n\n"
            f"Original Script:\n{original_script}\n\n"
            f"Error Message:\n{error_message}\n\n"
            "Please provide the corrected script only in response."
        )

        payload = {
            "model": self.model_name,
            "messages": [{"role": "system", "content": system_prompt}],
            "max_tokens": 2000,
            "temperature": 0.2,
        }

        try:
            response = await self._send_request(payload)
            content = response['choices'][0]['message']['content'].strip()

            # Extract script from the response
            import re
            script_match = re.search(r'```python\n(.*?)```', content, re.DOTALL)
            return script_match.group(1).strip() if script_match else None
        except Exception as e:
            logger.error(f"Error generating fixed script: {e}")
            raise

custom_llm = CustomLLMClient()