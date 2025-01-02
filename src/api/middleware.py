from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import time

from src.api.dependencies import identify_anonymous_user
from src.core.auth.jwt import create_access_token
from src.utils.metrics import HTTP_REQUEST_COUNT, HTTP_REQUEST_DURATION

class AnonymousUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip middleware for authentication endpoints
        if request.url.path.startswith("/api/v1/auth"):
            return await call_next(request)
            
        # Check for authorization header
        auth_header: Optional[str] = request.headers.get("Authorization")
        
        # If no auth header, create anonymous user
        if not auth_header:
            user = await identify_anonymous_user(request)
            token = create_access_token(data={"sub": user['id']})
            
            # Add authorization header to request
            request.headers.__dict__["_list"].append(
                (
                    "authorization".encode(),
                    f"Bearer {token}".encode()
                )
            )
            
        response = await call_next(request)
        return response

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get the route path if it exists, otherwise use the raw path
        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path
        
        try:
            response = await call_next(request)
            
            # Record metrics
            HTTP_REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
            
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error metrics
            HTTP_REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=500
            ).inc()
            raise
