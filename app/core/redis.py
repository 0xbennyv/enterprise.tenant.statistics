# app/core/redis.py
import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
)
# import redis.asyncio as redis
# from app.core.config import settings

# redis_client = redis.from_url(
#     settings.REDIS_URL,
#     decode_responses=True,
# )
