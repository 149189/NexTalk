import json
import redis
from django.conf import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

def push_short_message(session_id: str, message: dict):
    key = f"chat:{session_id}:messages"
    r.rpush(key, json.dumps(message))
    # trim to last N messages
    r.ltrim(key, -settings.SHORT_TERM_MAX_MESSAGES, -1)

def get_short_messages(session_id: str):
    key = f"chat:{session_id}:messages"
    raw = r.lrange(key, 0, -1)
    return [json.loads(x) for x in raw]

def clear_short_messages(session_id: str):
    key = f"chat:{session_id}:messages"
    r.delete(key)
