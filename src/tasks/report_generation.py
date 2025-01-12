from celery import Task
from uuid import UUID

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    update_backtest_status,
    update_backtest_urls
)
from src.infrastructure.storage.s3_client import S3Client
from src.infrastructure.llm.openai_client import generate_backtest_report
from src.infrastructure.llm.localllm_client import CustomLLMClient
from src.utils.logger import get_logger
import asyncio
import requests
import tempfile
import os

from src.constants.backtests import (
    BACKTEST_STATUS_REPORT_GENERATION_IN_PROGRESS,
    BACKTEST_STATUS_REPORT_GENERATION_FAILED,
    BACKTEST_STATUS_REPORT_GENERATION_SUCCESSFUL
)

from src.infrastructure.queue.instrumentation import track_celery_task


logger = get_logger(__name__)

class ReportGenerationTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        backtest_id = kwargs.get('backtest_id')
        if backtest_id:
            with get_db() as conn:
                logger.error(f"Report generation failed for backtest {backtest_id}: {str(exc)}")
                update_backtest_status(
                    conn,
                    backtest_id,
                    BACKTEST_STATUS_REPORT_GENERATION_FAILED,
                    str(exc)
                )

@celery_app.task(
    bind=True,
    base=ReportGenerationTask,
    name="src.tasks.report_generation.generate_report"
)
@track_celery_task("report_generation")
def generate_report(self, backtest_id: UUID):
    """Generate backtest report from execution logs"""
    with get_db() as conn:
        try:            
            with tempfile.TemporaryDirectory() as temp_dir:
                log_path = os.path.join(temp_dir, "backtest.log")
                logger.info(f"Starting report generation for backtest {backtest_id}")
                
                # Update status to generating report
                backtest = update_backtest_status(conn, backtest_id, BACKTEST_STATUS_REPORT_GENERATION_IN_PROGRESS)
                
                async def download_files():
                    # Download script using HTTP
                    response = requests.get(backtest['log_file_url'])
                    with open(log_path, 'wb') as log_file:
                        log_file.write(response.content)

                # Download log file
                asyncio.run(download_files())

                with open(log_path, 'r') as log_file:
                    log_content = log_file.read()
                
                # Generate report using LLM
                # custom_llm = CustomLLMClient()
                report_content = asyncio.run(generate_backtest_report(log_content))
                
                # Initialize S3 client
                s3_client = S3Client()
                
                # Upload report to S3
                report_key = f"{backtest_id}/report.md"
                s3_client.upload_file_content(
                    report_key,
                    report_content,
                    content_type="text/markdown"
                )
                
                # Update backtest record with report URL
                report_url = s3_client.get_file_url(report_key)
                backtest = update_backtest_urls(
                    conn,
                    backtest_id,
                    report_url=report_url
                )
                
                # Mark report as generated
                backtest = update_backtest_status(
                    conn,
                    backtest_id,
                    BACKTEST_STATUS_REPORT_GENERATION_SUCCESSFUL,
                    generated_report=True
                )
                
                logger.info(f"Report generation completed for backtest {backtest_id}")
            
        except Exception as e:
            logger.error(f"Report generation failed for backtest {backtest_id}: {str(e)}")
            update_backtest_status(
                conn,
                backtest_id,
                BACKTEST_STATUS_REPORT_GENERATION_FAILED,
                str(e)
            )
            raise
