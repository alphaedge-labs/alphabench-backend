import redis
from src.config.settings import settings

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    def set(self, key: str, value: str, ex: int = None):
        """Set a value in Redis with an optional expiration time."""
        return self.client.set(key, value, ex=ex)

    def get(self, key: str):
        """Get a value from Redis."""
        return self.client.get(key)

    def delete(self, key: str):
        """Delete a key from Redis."""
        return self.client.delete(key)

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        return self.client.exists(key) > 0

    def flushdb(self):
        """Flush the entire Redis database."""
        return self.client.flushdb()

redis_client = RedisClient()
