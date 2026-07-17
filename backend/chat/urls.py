from django.urls import path
from .views import QueryView, ChatSessionListCreateView, ChatMessageListView

urlpatterns = [
    path('query/', QueryView.as_view(), name='chat-query'),
    path('sessions/', ChatSessionListCreateView.as_view(), name='chat-sessions'),
    path('sessions/<int:session_id>/messages/', ChatMessageListView.as_view(), name='chat-messages'),
]
