from celery import Task
from uuid import UUID

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    get_backtest_by_id,
    update_backtest_status,
    update_backtest_urls
)
from src.infrastructure.llm.openai_client import generate_backtest_script
from src.infrastructure.storage.s3_client import S3Client

class ScriptGenerationTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        backtest_id = kwargs.get('backtest_id')
        if backtest_id:
            with get_db() as conn:
                update_backtest_status(
                    conn,
                    backtest_id,
                    "failed",
                    str(exc)
                )

@celery_app.task(
    bind=True,
    base=ScriptGenerationTask,
    name="src.tasks.script_generation.generate_backtest_script"
)
async def generate_backtest_script_task(self, backtest_id: UUID):
    """Generate backtest script and prepare data files"""
    with get_db() as conn:
        try:
            # Update status to processing
            backtest = update_backtest_status(conn, backtest_id, "generating_script")
            
            # Generate script using LLM
            script, data_points = await generate_backtest_script(
                backtest['strategy_description']
            )
            
            # Initialize S3 client
            s3_client = S3Client()
            
            # Upload script to S3
            script_key = f"{backtest_id}/script.py"
            await s3_client.upload_file_content(
                script_key,
                script,
                content_type="text/plain"
            )
            
            # Update backtest record with script URL
            script_url = s3_client.get_file_url(script_key)
            backtest = update_backtest_urls(
                conn,
                backtest_id,
                python_script_url=script_url
            )
            
            # Generate and upload validation dataset
            validation_data = "date,close,volume\n"  # Placeholder
            validation_key = f"{backtest_id}/validation_data.csv"
            await s3_client.upload_file_content(
                validation_key,
                validation_data,
                content_type="text/csv"
            )
            
            # Generate and upload full dataset
            full_data = "date,close,volume\n"  # Placeholder
            full_data_key = f"{backtest_id}/full_data.csv"
            await s3_client.upload_file_content(
                full_data_key,
                full_data,
                content_type="text/csv"
            )
            
            # Update backtest record with data URLs
            validation_url = s3_client.get_file_url(validation_key)
            full_data_url = s3_client.get_file_url(full_data_key)
            backtest = update_backtest_urls(
                conn,
                backtest_id,
                validation_data_url=validation_url,
                full_data_url=full_data_url
            )
            
            # Update status to ready for validation
            update_backtest_status(conn, backtest_id, "ready_for_validation")
            
            # Queue validation task
            from src.tasks.script_validation import validate_backtest_script
            validate_backtest_script.delay(backtest_id=backtest_id)
            
        except Exception as e:
            update_backtest_status(
                conn,
                backtest_id,
                "failed",
                str(e)
            )
            raise
