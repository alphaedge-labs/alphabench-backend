from prometheus_client import Counter, Histogram, Gauge
import time
from typing import Callable
from functools import wraps
import asyncio

# API Metrics
HTTP_REQUEST_COUNT = Counter(
    'http_request_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Backtest Metrics
BACKTEST_REQUEST_COUNT = Counter(
    'backtest_request_total',
    'Total number of backtest requests',
    ['status']
)

BACKTEST_PROCESSING_DURATION = Histogram(
    'backtest_processing_duration_seconds',
    'Backtest processing duration in seconds',
    ['stage']  # stages: script_generation, validation, execution, report_generation
)

BACKTEST_QUEUE_SIZE = Gauge(
    'backtest_queue_size',
    'Number of backtests in queue',
    ['stage']
)

# LLM Metrics
LLM_REQUEST_COUNT = Counter(
    'llm_request_total',
    'Total number of LLM API requests',
    ['operation', 'status']  # operations: title_generation, script_generation, report_generation
)

LLM_REQUEST_DURATION = Histogram(
    'llm_request_duration_seconds',
    'LLM API request duration in seconds',
    ['operation']
)

# S3 Metrics
S3_OPERATION_COUNT = Counter(
    's3_operation_total',
    'Total number of S3 operations',
    ['operation', 'status']  # operations: upload, download, delete
)

S3_OPERATION_DURATION = Histogram(
    's3_operation_duration_seconds',
    'S3 operation duration in seconds',
    ['operation']
)

def track_time(metric: Histogram) -> Callable:
    """Decorator to track function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
