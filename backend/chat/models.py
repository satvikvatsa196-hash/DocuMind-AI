from django.db import models
from django.conf import settings
from documents.models import DocumentCollection

class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    collection = models.ForeignKey(DocumentCollection, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} - {self.user.username}"

class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('USER', 'User'),
        ('AI', 'AI'),
    )
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} at {self.timestamp}"
