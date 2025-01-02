from typing import Dict, Any
import psycopg2
import redis
import boto3
from botocore.exceptions import ClientError
from openai import AsyncOpenAI

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def check_database() -> Dict[str, Any]:
    """Check PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT
        )
        conn.close()
        return {
            "status": "healthy",
            "latency_ms": 0  # TODO: Add actual latency measurement
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_redis() -> Dict[str, Any]:
    """Check Redis connection"""
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            socket_timeout=5
        )
        redis_client.ping()
        return {
            "status": "healthy",
            "latency_ms": 0  # TODO: Add actual latency measurement
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_s3() -> Dict[str, Any]:
    """Check S3 connection"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        return {
            "status": "healthy",
            "latency_ms": 0  # TODO: Add actual latency measurement
        }
    except ClientError as e:
        logger.error(f"S3 health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_openai() -> Dict[str, Any]:
    """Check OpenAI API connection"""
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        await client.models.list()
        return {
            "status": "healthy",
            "latency_ms": 0  # TODO: Add actual latency measurement
        }
    except Exception as e:
        logger.error(f"OpenAI health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_celery() -> Dict[str, Any]:
    """Check Celery workers status"""
    try:
        from src.infrastructure.queue.celery_app import celery_app
        
        # Get active workers
        active_workers = celery_app.control.inspect().active()
        
        if not active_workers:
            return {
                "status": "unhealthy",
                "error": "No active workers found"
            }
        
        # Check each queue has workers
        queues = [
            "script_generation",
            "script_validation",
            "backtest_execution",
            "report_generation"
        ]
        
        missing_queues = []
        for queue in queues:
            if not any(queue in worker_queues 
                      for worker in active_workers.values() 
                      for worker_queues in worker['active']):
                missing_queues.append(queue)
        
        if missing_queues:
            return {
                "status": "degraded",
                "missing_queues": missing_queues
            }
        
        return {
            "status": "healthy",
            "worker_count": len(active_workers)
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 