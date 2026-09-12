"""Redis client setup and initialization."""

import structlog
import redis.asyncio as aioredis

from app.config import Settings

logger = structlog.get_logger()

_redis_client: aioredis.Redis | None = None


async def init_redis(settings: Settings) -> aioredis.Redis:
    """Initialize and return the async Redis client."""
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    # Test connection
    await _redis_client.ping()
    logger.info("Redis client initialized", url=settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis:
    """Get the initialized Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client
