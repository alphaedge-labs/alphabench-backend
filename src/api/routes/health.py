from fastapi import APIRouter, Response, status
from typing import Dict, Any

from src.utils.health import (
    check_database,
    check_redis,
    check_s3,
    check_openai,
    check_celery
)
from src.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/health", tags=["health"])
logger = get_logger(__name__)

@router.get("")
async def health_check() -> Dict[str, str]:
    """Basic health check"""
    return {"status": "healthy"}

@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check of all system components"""
    health_status = {
        "database": await check_database(),
        "redis": await check_redis(),
        "s3": await check_s3(),
        "openai": await check_openai(),
        "celery": await check_celery()
    }
    
    # Determine overall status
    if any(component["status"] == "unhealthy" 
           for component in health_status.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health_status["status"] = "unhealthy"
    elif any(component["status"] == "degraded" 
            for component in health_status.values()):
        response.status_code = status.HTTP_200_OK
        health_status["status"] = "degraded"
    else:
        response.status_code = status.HTTP_200_OK
        health_status["status"] = "healthy"
    
    return health_status

@router.get("/ready")
async def readiness_check(response: Response) -> Dict[str, str]:
    """Readiness probe for Kubernetes"""
    try:
        # Check critical components
        db_status = await check_database()
        redis_status = await check_redis()
        
        if (db_status["status"] == "healthy" and 
            redis_status["status"] == "healthy"):
            return {"status": "ready"}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "not ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready"}

@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness probe for Kubernetes"""
    return {"status": "alive"} 