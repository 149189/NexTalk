from django.urls import path
from .views import ChatAPIView, MemoryListCreateAPIView, SessionMessagesAPIView, chat_view

urlpatterns = [
    path("api/chat/", chat_view, name="chat"),
    path("chat/", ChatAPIView.as_view(), name="chat"),
    path("memory/<uuid:user_profile_id>/", MemoryListCreateAPIView.as_view(), name="memory-list-create"),
    path("session/<str:session_id>/messages/", SessionMessagesAPIView.as_view(), name="session-messages"),
]
