import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from nextalk.models import UserProfile, Memory
import fakeredis
from nextalk import redis_utils

User = get_user_model()

@pytest.mark.django_db
def test_memory_crud(client):
    user = User.objects.create(username="tester")
    up = UserProfile.objects.create(user=user, display_name="Tester")

    url = reverse("memory-list-create", args=[up.id])
    res = client.post(url, {"mem_type":"bio", "content":"I love sushi."}, content_type="application/json")
    assert res.status_code == 201
    assert Memory.objects.filter(user_profile=up, content__icontains="sushi").exists()

@pytest.mark.django_db
def test_short_term_buffer_trimming(monkeypatch):
    # monkeypatch redis client in redis_utils to use fakeredis
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(redis_utils, "r", fake)

    session_id = "sess1"
    # push > SHORT_TERM_MAX_MESSAGES
    for i in range(30):
        redis_utils.push_short_message(session_id, {"role":"user", "text": f"m{i}"})
    msgs = redis_utils.get_short_messages(session_id)
    from django.conf import settings
    assert len(msgs) <= settings.SHORT_TERM_MAX_MESSAGES
