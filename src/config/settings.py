from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    DEBUG: bool = True

    # FastAPI
    PORT: int = 8000

    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # AWS settings
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET_NAME: str

    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str

    # Local running llm model
    LOCAL_LLM_SERVER_URL: str
    LOCAL_LLM_MODEL_NAME: str

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate limiting
    ANONYMOUS_DAILY_LIMIT: int = 3
    AUTHENTICATED_DAILY_LIMIT: int = 5

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


settings = Settings()
