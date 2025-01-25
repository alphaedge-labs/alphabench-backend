from celery import Task
from uuid import UUID
import subprocess
import tempfile
import os
import asyncio
                

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    update_backtest_status
)

from src.infrastructure.storage.s3_client import S3Client
from src.infrastructure.queue.instrumentation import track_celery_task
from src.infrastructure.llm.openai_client import fix_backtest_script

from src.constants.backtests import (
    BACKTEST_STATUS_VALIDATION_FAILED,
    BACKTEST_STATUS_VALIDATION_IN_PROGRESS,
    BACKTEST_STATUS_VALIDATION_PASSED,
    BACKTEST_STATUS_SCRIPT_GENERATION_IN_PROGRESS
)

from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRY_ATTEMPTS = 3  # Configure max retries

class ScriptValidationTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        backtest_id = kwargs.get('backtest_id')
        if backtest_id:
            with get_db() as conn:
                update_backtest_status(
                    conn,
                    backtest_id,
                    BACKTEST_STATUS_VALIDATION_FAILED,
                    str(exc)
                )

@celery_app.task(
    bind=True,
    base=ScriptValidationTask,
    name="src.tasks.script_validation.validate_backtest_script"
)
@track_celery_task("validation")
def validate_backtest_script(self, backtest_id: UUID, attempt: int = 1):
    """Validate the generated backtest script with retry logic"""
    with get_db() as conn:
        try:
            # Update status to validating
            update_backtest_status(conn, backtest_id, BACKTEST_STATUS_VALIDATION_IN_PROGRESS)
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download script and validation data
                script_path = os.path.join(temp_dir, "script.py")
                data_path = os.path.join(temp_dir, "validation_data.csv")
                log_path = os.path.join(temp_dir, "backtest.log")
                
                s3_client = S3Client()

                script_key = f"{backtest_id}/script.py"
                data_key = f"{backtest_id}/validation_data.csv"

                async def download_files():
                    await asyncio.gather(
                        s3_client.download_file(script_key, script_path),
                        s3_client.download_file(data_key, data_path)
                    )
                
                # Run the async download function
                asyncio.run(download_files())
                logger.info(f'Downloading files for backtest: {backtest_id}')
                
                # Make script executable
                os.chmod(script_path, 0o755)
                
                # Run script with validation data
                logger.info(f"Running script with validation data for backtest: {backtest_id}")

                try:
                    result = subprocess.run(
                        ["python", script_path, "--data", data_path, "--log", log_path],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    logger.info(f"Script execution output - stdout:\n{result.stdout}")
                    logger.info(f"Script execution output - stderr:\n{result.stderr}")
                except subprocess.TimeoutExpired as e:
                    logger.error(f"Script timed out for backtest {backtest_id}. Last stdout: {e.stdout}\nLast stderr: {e.stderr}")
                    raise
                
                if result.returncode != 0:
                    logger.error(f"Validation failed. Subprocess result: {result}")
                    raise Exception(f"Validation failed: {result.stderr}")

                logger.info(f"Successfully validated script for backtest: {backtest_id}")

                # Update status to validation successful
                update_backtest_status(
                    conn, 
                    backtest_id, 
                    BACKTEST_STATUS_VALIDATION_PASSED
                )
                
                # Queue full backtest execution
                from src.tasks.backtest_execution import execute_backtest
                execute_backtest.delay(backtest_id=backtest_id)
                logger.info(f"Queued execution task for backtesting: {backtest_id}")
            
        except (subprocess.TimeoutExpired, Exception) as e:
            error_message = str(e)
            if isinstance(e, subprocess.TimeoutExpired):
                error_message = f"Script execution timed out after 300 seconds"
            
            if attempt < MAX_RETRY_ATTEMPTS:
                logger.info(f"Validation attempt {attempt} failed, trying to fix script...")
                
                # Read the current script
                with open(script_path, 'r') as f:
                    current_script = f.read()
                
                # Get improved script from GPT
                improved_script = asyncio.run(fix_backtest_script(
                    script=current_script,
                    error_message=error_message
                ))
                
                if improved_script:
                    # Upload improved script
                    s3_client = S3Client()
                    script_key = f"{backtest_id}/script.py"
                    s3_client.upload_file_content(
                        script_key,
                        improved_script,
                        content_type="text/plain"
                    )
                    
                    # Update status
                    update_backtest_status(
                        conn,
                        backtest_id,
                        BACKTEST_STATUS_SCRIPT_GENERATION_IN_PROGRESS,
                        f"Retrying with improved script. Attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}"
                    )
                    
                    # Queue new validation attempt
                    validate_backtest_script.delay(
                        backtest_id=backtest_id,
                        attempt=attempt + 1
                    )
                    return
                
            # If max attempts reached or no improvement possible
            update_backtest_status(
                conn,
                backtest_id,
                BACKTEST_STATUS_VALIDATION_FAILED,
                f"Validation failed after {attempt} attempts. Last error: {error_message}"
            )
            raise Exception(f"Validation failed after {attempt} attempts. Last error: {error_message}")