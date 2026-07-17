from rest_framework import permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from ai_engine.retriever import RetrieverService
from ai_engine.llm import LLMService
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer
from django.shortcuts import get_object_or_404

class ChatSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatMessageListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs['session_id']
        session = get_object_or_404(ChatSession, id=session_id, user=self.request.user)
        return ChatMessage.objects.filter(session=session).order_by('timestamp')

class QueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        query = request.data.get("query")
        session_id = request.data.get("session_id")
        document_ids = request.data.get("document_ids", None)
        
        if not query:
            return Response({"error": "Query is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        session = None
        chat_history = []
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
            # Limit history to last 10 messages (5 turns)
            recent_messages = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:10]
            for msg in reversed(recent_messages):
                chat_history.append({
                    "role": msg.role,
                    "content": msg.message
                })
            
            # Save user query to db
            ChatMessage.objects.create(session=session, role='USER', message=query)
            
        # 1. Retrieve Context
        context_chunks = RetrieverService.retrieve_context(query, document_ids=document_ids, top_k=5)
        
        # 2. Call LLM
        llm_service = LLMService()
        response_data = llm_service.generate_answer(query, context_chunks, chat_history)
        
        # Save AI response to db
        if session:
            ChatMessage.objects.create(session=session, role='AI', message=response_data.get("answer", ""))
        
        return Response(response_data, status=status.HTTP_200_OK)
