from rest_framework import serializers
from .models import Memory, UserProfile

class MemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = ["id", "user_profile", "mem_type", "content", "created_at", "last_used_at"]

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["id", "display_name", "timezone", "preferences", "created_at"]
