# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from prometheus_client import make_asgi_app
from fastapi.websockets import WebSocket, WebSocketDisconnect

from src.api.middleware import AnonymousUserMiddleware, PrometheusMiddleware
from src.api.routes import auth, backtests, reports, subscriptions, health, users
from src.api.services.websocket import manager

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="alphabench API",
        version="1.0.0",
        description="""
        alphabench is a backtesting platform that allows users to describe trading strategies in natural language 
        and receive detailed backtesting reports.
        
        ## Features
        
        * Natural language strategy description
        * Automated Python script generation
        * Comprehensive backtesting
        * Detailed performance reports
        * Google OAuth authentication
        * Rate limiting based on subscription
        
        ## Authentication
        
        The API uses JWT tokens for authentication. You can obtain a token by:
        1. Authenticating with Google OAuth
        2. Using the token in the Authorization header: `Bearer <token>`
        
        Anonymous users are automatically assigned a token based on IP and MAC address.
        
        ## Rate Limits
        
        * Anonymous users: 3 reports/day
        * Authenticated users: 5 reports/day
        * Subscribed users: Configurable limit (n reports/day)
        """,
        routes=app.routes,
    )
    
    # Custom extension to add authentication flows
    openapi_schema["components"]["securitySchemes"] = {
        "GoogleOAuth": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth",
                    "tokenUrl": "https://oauth2.googleapis.com/token",
                    "scopes": {
                        "openid": "OpenID Connect",
                        "email": "Email address",
                        "profile": "User profile"
                    }
                }
            }
        },
        "JWT": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(
    title="alphabench API",
    description="API for alphabench backtesting platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Customize OpenAPI schema
app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add anonymous user middleware
app.add_middleware(AnonymousUserMiddleware)

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(backtests.router)
app.include_router(reports.router)
app.include_router(subscriptions.router)
app.include_router(health.router)
app.include_router(users.router)

# Create metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id=user_id, websocket=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
