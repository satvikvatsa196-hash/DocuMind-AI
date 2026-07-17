from rest_framework import serializers
from .models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'session', 'role', 'message', 'timestamp')
        read_only_fields = ('id', 'session', 'role', 'timestamp')

class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ('id', 'user', 'collection', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')
