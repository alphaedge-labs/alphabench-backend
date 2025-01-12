from functools import wraps
from src.utils.metrics import (
    BACKTEST_REQUEST_COUNT,
    BACKTEST_PROCESSING_DURATION,
    BACKTEST_QUEUE_SIZE,
    LLM_REQUEST_COUNT,
    LLM_REQUEST_DURATION
)
import time

def track_celery_task(stage):
    """
    Decorator to track Celery task metrics in Prometheus
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Increment queue size when task starts
            BACKTEST_QUEUE_SIZE.labels(stage=stage).inc()
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                # Record successful completion
                BACKTEST_REQUEST_COUNT.labels(status="success").inc()
                return result
            except Exception as e:
                # Record failure
                BACKTEST_REQUEST_COUNT.labels(status="failed").inc()
                raise
            finally:
                # Record processing duration
                duration = time.time() - start_time
                BACKTEST_PROCESSING_DURATION.labels(stage=stage).observe(duration)
                # Decrement queue size when task completes
                BACKTEST_QUEUE_SIZE.labels(stage=stage).dec()
        return wrapper
    return decorator 

def track_llm_operation(operation):
    """
    Decorator to track LLM operations metrics in Prometheus
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                LLM_REQUEST_COUNT.labels(
                    operation=operation,
                    status="success"
                ).inc()
                return result
            except Exception as e:
                LLM_REQUEST_COUNT.labels(
                    operation=operation,
                    status="failed"
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                LLM_REQUEST_DURATION.labels(operation=operation).observe(duration)
        return wrapper
    return decorator 