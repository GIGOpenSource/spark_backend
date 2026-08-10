import os
import redis

r = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', ''),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)
