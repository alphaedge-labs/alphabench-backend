from celery import Celery
from src.config.settings import settings

celery_app = Celery(
    "alphabench",
    broker=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    include=[
        "src.tasks.script_generation",
        "src.tasks.script_validation",
        "src.tasks.backtest_execution",
        "src.tasks.report_generation"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.tasks.script_generation.*": {"queue": "script_generation"},
        "src.tasks.script_validation.*": {"queue": "script_validation"},
        "src.tasks.backtest_execution.*": {"queue": "backtest_execution"},
        "src.tasks.report_generation.*": {"queue": "report_generation"},
    }
)
