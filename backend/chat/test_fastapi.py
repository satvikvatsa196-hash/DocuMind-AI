import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from fastapi.testclient import TestClient
from chat.fastapi_stream import app
import jwt
from django.conf import settings
from chat.models import ChatSession, ChatMessage
from documents.models import Document, DocumentCollection
from ai_engine.retriever import RetrieverService

User = get_user_model()

class FastAPIStreamingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client = TestClient(app)
        
        # Create a valid token
        payload = {"user_id": self.user.id}
        self.token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        self.session = ChatSession.objects.create(user=self.user, title="Test Session")
        
    @patch('chat.fastapi_stream.RetrieverService.retrieve_context')
    @patch('chat.fastapi_stream.LLMService')
    def test_successful_streaming(self, mock_llm_service_class, mock_retrieve_context):
        mock_retrieve_context.return_value = [{"text": "Context chunk", "metadata": {"source": "doc1.pdf", "page_number": "1"}}]
        
        # Setup async generator mock for stream_generate_answer
        mock_llm_service = mock_llm_service_class.return_value
        
        async def mock_stream(*args, **kwargs):
            yield {"token": "Hello "}
            yield {"token": "World!"}
            yield {"citations": [{"document_name": "doc1.pdf", "page_number": "1"}]}
            
        mock_llm_service.stream_generate_answer = mock_stream
        
        response = self.client.post("/stream/", json={
            "query": "Hello",
            "session_id": self.session.id
        }, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        
        lines = response.text.split("\n\n")
        
        # Verify tokens were streamed
        self.assertTrue(any('"Hello "' in line for line in lines))
        self.assertTrue(any('"World!"' in line for line in lines))
        self.assertTrue(any('"citations"' in line for line in lines))
        self.assertTrue(any('event: end' in line for line in lines))
        
        # Verify message was saved to DB
        messages = ChatMessage.objects.filter(session=self.session, role='AI')
        self.assertEqual(messages.count(), 1)
        self.assertEqual(messages.first().message, "Hello World!")
        
    @patch('chat.fastapi_stream.RetrieverService.retrieve_context')
    @patch('chat.fastapi_stream.LLMService')
    def test_client_disconnect_during_streaming(self, mock_llm_service_class, mock_retrieve_context):
        mock_retrieve_context.return_value = [{"text": "Context chunk", "metadata": {"source": "doc1.pdf", "page_number": "1"}}]
        
        mock_llm_service = mock_llm_service_class.return_value
        
        async def mock_stream(*args, **kwargs):
            yield {"token": "Started..."}
            raise asyncio.CancelledError("Client disconnected")
            
        mock_llm_service.stream_generate_answer = mock_stream
        
        response = self.client.post("/stream/", json={
            "query": "Hello",
            "session_id": self.session.id
        }, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify partial message was saved to DB upon disconnect
        messages = ChatMessage.objects.filter(session=self.session, role='AI')
        self.assertEqual(messages.count(), 1)
        self.assertEqual(messages.first().message, "Started...")
