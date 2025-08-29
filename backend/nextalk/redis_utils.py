import json
import redis
from django.conf import settings

# Fallbacks in case not defined in settings
REDIS_HOST = getattr(settings, "REDIS_HOST", "redis")
REDIS_PORT = getattr(settings, "REDIS_PORT", 6379)
REDIS_DB = getattr(settings, "REDIS_DB", 0)
SHORT_TERM_MAX_MESSAGES = getattr(settings, "SHORT_TERM_MAX_MESSAGES", 20)

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

def push_short_message(session_id: str, message: dict):
    key = f"chat:{session_id}:messages"
    r.rpush(key, json.dumps(message))
    # Trim to last N messages
    r.ltrim(key, -SHORT_TERM_MAX_MESSAGES, -1)

def get_short_messages(session_id: str):
    key = f"chat:{session_id}:messages"
    raw = r.lrange(key, 0, -1)
    return [json.loads(x) for x in raw]

def clear_short_messages(session_id: str):
    key = f"chat:{session_id}:messages"
    r.delete(key)
