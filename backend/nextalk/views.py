from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Memory, UserProfile
from .serializers import MemorySerializer, UserProfileSerializer
from .redis_utils import push_short_message, get_short_messages, clear_short_messages
from .llm import call_llm, get_embedding

class ChatAPIView(APIView):
    """
    POST /api/chat/
    body: { "session_id": "...", "user_profile_id": "...", "message": "..." }
    """
    def post(self, request):
        data = request.data
        session_id = data["session_id"]
        user_profile_id = data.get("user_profile_id")
        user_msg = data["message"]

        # save short-term user message
        user_msg_obj = {"role": "user", "text": user_msg, "ts": timezone.now().isoformat()}
        push_short_message(session_id, user_msg_obj)

        # fetch short-term history and top long-term facts (simple strategy)
        short_history = get_short_messages(session_id)  # list of messages dict
        long_term = []
        if user_profile_id:
            up = get_object_or_404(UserProfile, id=user_profile_id)
            # fetch recent N memories
            long_term = list(up.memories.all().order_by("-last_used_at", "-created_at")[:5])

        # compose prompt
        prompt_parts = []
        prompt_parts.append("Relevant long-term memories:")
        for m in long_term:
            prompt_parts.append(f"- {m.content}")
        prompt_parts.append("\nRecent conversation:")
        for m in short_history:
            prompt_parts.append(f"{m['role']}: {m['text']}")
        prompt_parts.append("\nUser: " + user_msg)
        prompt = "\n".join(prompt_parts)

        # call LLM
        reply_text = call_llm(prompt)

        # save assistant reply to short term
        assistant_obj = {"role": "assistant", "text": reply_text, "ts": timezone.now().isoformat()}
        push_short_message(session_id, assistant_obj)

        # mark used long-term memories' last_used_at
        for m in long_term:
            m.last_used_at = timezone.now()
            m.save(update_fields=["last_used_at"])

        # optionally: detect saveable memory (very naive)
        save_suggestion = None
        if "my favorite" in user_msg.lower() or "i like" in user_msg.lower():
            save_suggestion = {"suggest": True, "example_save": user_msg}

        return Response({
            "reply": reply_text,
            "short_history": short_history[-10:],
            "save_suggestion": save_suggestion
        }, status=status.HTTP_200_OK)

class MemoryListCreateAPIView(APIView):
    def get(self, request, user_profile_id):
        up = get_object_or_404(UserProfile, id=user_profile_id)
        mems = up.memories.all().order_by("-created_at")
        serializer = MemorySerializer(mems, many=True)
        return Response(serializer.data)

    def post(self, request, user_profile_id):
        up = get_object_or_404(UserProfile, id=user_profile_id)
        serializer = MemorySerializer(data={**request.data, "user_profile": str(up.id)})
        if serializer.is_valid():
            mem = serializer.save()
            return Response(MemorySerializer(mem).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SessionMessagesAPIView(APIView):
    def get(self, request, session_id):
        msgs = get_short_messages(session_id)
        return Response(msgs)

    def post(self, request, session_id):
        # clear or push - simple control: { action: "clear" }
        action = request.data.get("action")
        if action == "clear":
            clear_short_messages(session_id)
            return Response({"status":"cleared"})
        return Response({"detail":"unknown action"}, status=status.HTTP_400_BAD_REQUEST)
