from celery import Task
from uuid import UUID
import subprocess
import tempfile
import os
from datetime import datetime
import asyncio
import requests

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    get_backtest_by_id,
    update_backtest_status,
    update_backtest_urls
)
from src.infrastructure.storage.s3_client import S3Client

import logging
logger = logging.getLogger()

class BacktestExecutionTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        backtest_id = kwargs.get('backtest_id')
        if backtest_id:
            with get_db() as conn:
                update_backtest_status(
                    conn,
                    backtest_id,
                    "execution_failed",
                    str(exc)
                )

@celery_app.task(
    bind=True,
    base=BacktestExecutionTask,
    name="src.tasks.backtest_execution.execute_backtest"
)
def execute_backtest(self, backtest_id: UUID):
    """Execute the validated backtest script with full dataset"""
    with get_db() as conn:
        try:
            # Update status to executing
            backtest = update_backtest_status(conn, backtest_id, "executing")
            
            # Initialize S3 client
            s3_client = S3Client()
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download script and full dataset
                script_path = os.path.join(temp_dir, "script.py")
                data_path = os.path.join(temp_dir, "full_data.csv")
                log_path = os.path.join(temp_dir, "backtest.log")
                
                async def download_files():
                    # Download script using HTTP
                    response = requests.get(backtest['python_script_url'])
                    with open(script_path, 'wb') as script_file:
                        script_file.write(response.content)

                    # Download validation data using HTTP
                    response = requests.get(backtest['full_data_url'])
                    with open(data_path, 'wb') as data_file:
                        data_file.write(response.content)

                # Run the async download function
                asyncio.run(download_files())

                # Make script executable
                os.chmod(script_path, 0o755)
                
                # Run script with full dataset
                with open(log_path, 'w') as log_file:
                    result = subprocess.run(
                        [
                            "python",
                            script_path,
                            "--data",
                            data_path,
                            "--log",
                            log_path
                        ],
                        capture_output=True,
                        text=True,
                        timeout=1800  # 30 minute timeout
                    )
                
                if result.returncode != 0:
                    raise Exception(f"Execution failed: {result.stderr}")
                
                # Upload log file to S3
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                log_key = f"{backtest_id}/backtest_{timestamp}.log"
                
                asyncio.run(s3_client.upload_file(
                    log_path,
                    log_key
                ))
                logger.info(f'Uploading log file for backtest: {backtest_id}')
                
                # Update backtest record with log URL
                log_url = s3_client.get_file_url(log_key)
                update_backtest_urls(
                    conn,
                    backtest_id,
                    log_file_url=log_url
                )
                
                # Update status and mark ready for report
                update_backtest_status(
                    conn,
                    backtest_id,
                    "execution_successful"
                )
                
                # Queue report generation
                from src.tasks.report_generation import generate_report
                generate_report.delay(backtest_id=backtest_id)
                
        except Exception as e:
            update_backtest_status(
                conn,
                backtest_id,
                "execution_failed",
                str(e)
            )
            raise
