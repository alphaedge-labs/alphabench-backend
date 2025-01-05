from celery import Task
import logging
from uuid import UUID

from src.infrastructure.queue.celery_app import celery_app
from src.db.base import get_db
from src.db.queries.backtests import (
    get_backtest_by_id,
    update_backtest_status,
    update_backtest_urls
)
from src.db.queries.tick_data import (
    get_available_columns,
    fetch_tick_data
)
from src.infrastructure.llm.openai_client import generate_backtest_script
from src.infrastructure.storage.s3_client import S3Client

# Set up logger
logger = logging.getLogger(__name__)

class ScriptGenerationTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        backtest_id = kwargs.get('backtest_id')
        if backtest_id:
            logger.error(f"Script generation failed for backtest {backtest_id}: {str(exc)}")
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
def generate_backtest_script_task(self, backtest_id: UUID):
    """Generate backtest script and prepare data files"""
    logger.info(f"Starting script generation for backtest {backtest_id}")
    with get_db() as conn:
        try:
            conn.autocommit = True  # Ensure we're not in a transaction
            # Update status to processing

            logger.info(f"Backtest ID: {backtest_id}")

            backtest = update_backtest_status(conn, backtest_id, "generating_script")

            if not backtest:
                raise Exception(f"Backtest record not found or could not be updated for ID: {backtest_id}")

            logger.info(f"Backtest record: {backtest}")
            
            available_columns = get_available_columns(
                conn,
                instrument_symbol=backtest["instrument_symbol"],
                from_date=backtest["from_date"],
                to_date=backtest["to_date"]
            )
            extra_message = f"Keep in mind that I have the following available columns in database for backtesting: {', '.join(available_columns)}. If the script requires any other data points than these, then simply return None as response."

            logger.info(f'Extra message: {extra_message}')

            # Generate script using LLM
            logger.info(f"Generating script using LLM for backtest {backtest_id}")

            import asyncio
            script, data_points = asyncio.run(generate_backtest_script(
                strategy_description=backtest['strategy_description'],
                extra_message=extra_message
            ))

            if not script and not data_points:
                # update backtest by saying we cannot backtest this yet
                raise Exception(f'Cannot generate script.')

            logger.info(f'Data points: {data_points}')
            logger.info(f"Generated script length: {len(script)} characters")

            # Initialize S3 client and upload files
            logger.info(f"Uploading files to S3 for backtest {backtest_id}")
            
            s3_client = S3Client()
            
            # Upload script to S3
            script_key = f"{backtest_id}/script.py"
            s3_client.upload_file_content(
                script_key,
                script,
                content_type="text/plain"
            )
            
            logger.info(f"Uploaded script to S3 for backtest {backtest_id}")

            logger.info(f'Fetching data required for {backtest["instrument_symbol"]} from {backtest["from_date"]} to {backtest["to_date"]}...')

            full_data = fetch_tick_data(
                conn=conn,
                instrument_symbol=backtest["instrument_symbol"],
                from_date=backtest["from_date"],
                to_date=backtest["to_date"],
                columns=data_points,
            )

            validation_data = full_data.head(100)

            validation_csv = validation_data.to_csv(index=False)
            full_data_csv = full_data.to_csv(index=False)
            
            # Generate and upload validation dataset
            validation_key = f"{backtest_id}/validation_data.csv"
            full_data_key = f"{backtest_id}/full_data.csv"

            s3_client.upload_file_content(
                validation_key,
                validation_csv,
                content_type="text/csv"
            )
            
            logger.info(f"Uploaded validation_data to S3 for backtest {backtest_id}")

            # Generate and upload full dataset
            s3_client.upload_file_content(
                full_data_key,
                full_data_csv,
                content_type="text/csv"
            )
            
            logger.info(f"Uploaded full_data to S3 for backtest {backtest_id}")
            
            # Update backtest record with data URLs
            validation_url = s3_client.get_file_url(validation_key)
            full_data_url = s3_client.get_file_url(full_data_key)
            script_url = s3_client.get_file_url(script_key)

            backtest = update_backtest_urls(
                conn,
                backtest_id,
                python_script_url=script_url,
                validation_data_url=validation_url,
                full_data_url=full_data_url
            )
            
            logger.info(f"Files uploaded successfully for backtest {backtest_id}")
            
            # Update status to ready for validation
            update_backtest_status(conn, backtest_id, "ready_for_validation")
            logger.info(f"Updated status to ready_for_validation for backtest {backtest_id}")

            # Queue validation task
            from src.tasks.script_validation import validate_backtest_script
            validate_backtest_script.delay(backtest_id=backtest_id)
            logger.info(f"Queued validation task for backtest {backtest_id}")
            
        except Exception as e:
            logger.error(f"Error in script generation for backtest {backtest_id}: {str(e)}", exc_info=True)
            update_backtest_status(
                conn,
                backtest_id,
                "failed",
                str(e)
            )
            raise
