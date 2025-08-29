# NexTalk
NexTalk is a fast, secure, and intuitive chat platform that makes conversations effortless. Whether for friends, teams, or communities, it keeps you connected with real-time messaging, seamless sharing, and a clean, modern interface.


# Chatbot Django (short-term + long-term memory)

## Quickstart (local)
1. python -m venv venv && source venv/bin/activate
2. pip install -r requirements.txt
3. cd backend
4. python manage.py migrate
5. python manage.py runserver

## Docker (recommended)
docker-compose up --build

## API
POST /api/chat/
  { "session_id": "...", "user_profile_id": "...", "message": "Hello" }

GET /api/memory/<user_profile_id>/
POST /api/memory/<user_profile_id>/ { mem_type, content }

GET /api/session/<session_id>/messages/
POST /api/session/<session_id>/messages/ { action: "clear" }

## Tests
pytest
