import httpx
from uuid import UUID
from src.config.settings import settings

from src.utils.logger import get_logger
logger = get_logger(__name__)

BASE_URL = f'http://alphabench__fastapi:{settings.PORT}'

async def post_backtest_update(backtest_id: UUID):
    """Send a POST request to update backtest status."""
    url = f"{BASE_URL}/v1/backtests/broadcast/{backtest_id}"
    async with httpx.AsyncClient() as client:  # Ensure proper resource cleanup
        try:
            response = await client.post(url)
            response.raise_for_status()
            return response.json()  # Return the parsed JSON response, if applicable
        except httpx.HTTPStatusError as http_err:
            # Log or handle HTTP errors specifically
            logger.warning(f"Postback failed for backtest. Response: {http_err.response}")
            logger.warning(f"HTTP error occurred: {http_err.response.status_code} - {http_err.response.text}")
            pass
        except httpx.RequestError as req_err:
            # Log or handle general request errors
            logger.warning(f"Request error occurred: {req_err}")
            pass