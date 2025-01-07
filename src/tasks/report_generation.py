from celery import Task
from uuid import UUID

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    get_backtest_by_id,
    update_backtest_status,
    update_backtest_urls
)
from src.infrastructure.storage.s3_client import S3Client
from src.infrastructure.llm.openai_client import generate_backtest_report
from src.infrastructure.llm.localllm_client import CustomLLMClient
from src.utils.logger import get_logger
import asyncio

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
                    "report_generation_failed",
                    str(exc)
                )

@celery_app.task(
    bind=True,
    base=ReportGenerationTask,
    name="src.tasks.report_generation.generate_report"
)
def generate_report(self, backtest_id: UUID):
    """Generate backtest report from execution logs"""
    with get_db() as conn:
        try:
            logger.info(f"Starting report generation for backtest {backtest_id}")
            
            # Update status to generating report
            backtest = update_backtest_status(conn, backtest_id, "generating_report")
            
            # Initialize S3 client
            s3_client = S3Client()
            
            # Download log file
            log_content = asyncio.run(s3_client.get_file_content(backtest['log_file_url']))
            
            # Generate report using LLM
            # custom_llm = CustomLLMClient()
            report_content = asyncio.run(generate_backtest_report(log_content))
            
            # Upload report to S3
            report_key = f"{backtest_id}/report.md"
            asyncio.run(s3_client.upload_file_content(
                report_key,
                report_content,
                content_type="text/markdown"
            ))
            
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
                "completed",
                ready_for_report=True,
                generated_report=True
            )
            
            logger.info(f"Report generation completed for backtest {backtest_id}")
            
        except Exception as e:
            logger.error(f"Report generation failed for backtest {backtest_id}: {str(e)}")
            update_backtest_status(
                conn,
                backtest_id,
                "report_generation_failed",
                str(e)
            )
            raise
