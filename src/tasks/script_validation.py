from celery import Task
from uuid import UUID
import subprocess
import tempfile
import os
import requests
import asyncio
                

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    get_backtest_by_id,
    update_backtest_status
)
from src.infrastructure.storage.s3_client import S3Client

import logging
logger = logging.getLogger()

class ScriptValidationTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        backtest_id = kwargs.get('backtest_id')
        if backtest_id:
            with get_db() as conn:
                update_backtest_status(
                    conn,
                    backtest_id,
                    "validation_failed",
                    str(exc)
                )

@celery_app.task(
    bind=True,
    base=ScriptValidationTask,
    name="src.tasks.script_validation.validate_backtest_script"
)
def validate_backtest_script(self, backtest_id: UUID):
    """Validate the generated backtest script"""
    with get_db() as conn:
        try:
            # Update status to validating
            backtest = update_backtest_status(conn, backtest_id, "validating")
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download script and validation data
                script_path = os.path.join(temp_dir, "script.py")
                data_path = os.path.join(temp_dir, "validation_data.csv")
                log_path = os.path.join(temp_dir, "backtest.log")
                
                async def download_files():
                    # Download script using HTTP
                    response = requests.get(backtest['python_script_url'])
                    with open(script_path, 'wb') as script_file:
                        script_file.write(response.content)

                    # Download validation data using HTTP
                    response = requests.get(backtest['validation_data_url'])
                    with open(data_path, 'wb') as data_file:
                        data_file.write(response.content)

                # Run the async download function
                asyncio.run(download_files())
                logger.info(f'Downloading files for backtest: {backtest_id}')
                
                # Make script executable
                os.chmod(script_path, 0o755)
                
                # Run script with validation data
                result = subprocess.run(
                    ["python", script_path, "--data", data_path, "--log", log_path],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    raise Exception(f"Validation failed: {result.stderr}")

                logger.info(f"Successfully validated script for backtest: {backtest_id}")

                # Update status to validation successful
                update_backtest_status(conn, backtest_id, "validation_successful")
                
                # Queue full backtest execution
                from src.tasks.backtest_execution import execute_backtest
                execute_backtest.delay(backtest_id=backtest_id)
                logger.info(f"Queued execution task for backtesting: {backtest_id}")
            
        except Exception as e:
            update_backtest_status(
                conn,
                backtest_id,
                "validation_failed",
                str(e)
            )
            raise
