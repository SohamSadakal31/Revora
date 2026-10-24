import json
import logging
import redis
from app.core.config import settings

redis_client = redis.StrictRedis.from_url(
    settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
)


# the cache only speeds things up - if Redis is down, predictions still work without it
def get_cached_prediction(key: str):
    try:
        value = redis_client.get(key)
    except redis.RedisError as e:
        logging.warning(f'Redis unavailable, skipping cache read: {e}')
        return None
    return json.loads(value) if value else None


def set_cached_prediction(key: str, value: dict):
    try:
        redis_client.set(key, json.dumps(value), ex=7 * 24 * 3600)
    except redis.RedisError as e:
        logging.warning(f'Redis unavailable, skipping cache write: {e}')
