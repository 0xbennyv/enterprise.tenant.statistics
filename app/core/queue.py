# app/core/queue.py
import os
from redis import Redis
import redis
from rq import Queue

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    db=0
)


telemetry_queue = Queue(
    "telemetry",
    connection=redis_client,
    default_timeout=7200,  # 2 hours
)
