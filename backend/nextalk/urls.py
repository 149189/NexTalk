from django.urls import path
from .views import ChatAPIView, MemoryListCreateAPIView, SessionMessagesAPIView

urlpatterns = [
    path("chat/", ChatAPIView.as_view(), name="chat"),
    path("memory/<uuid:user_profile_id>/", MemoryListCreateAPIView.as_view(), name="memory-list-create"),
    path("session/<str:session_id>/messages/", SessionMessagesAPIView.as_view(), name="session-messages"),
]
