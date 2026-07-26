import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import ChatSession, ChatMessage
from documents.models import Document, DocumentCollection

User = get_user_model()

class ChatQueryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test_chat', password='testpassword123')
        self.client.force_authenticate(user=self.user)
        self.query_url = reverse('chat-query')

    def test_query_no_input(self):
        response = self.client.post(self.query_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch('chat.views.RetrieverService.retrieve_context')
    @patch('chat.views.LLMService.generate_answer')
    def test_query_successful_response(self, mock_generate, mock_retrieve):
        # Mock Context Retrieval
        mock_retrieve.return_value = [
            {"text": "Python is a programming language.", "metadata": {"source": "python_doc.txt", "page_number": 1}}
        ]
        
        # Mock LLM Response
        expected_response = {
            "answer": "Python is a programming language.",
            "citations": [
                {
                    "document_name": "python_doc.txt",
                    "page_number": "1"
                }
            ]
        }
        mock_generate.return_value = expected_response

        response = self.client.post(self.query_url, {"query": "What is Python?"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], "Python is a programming language.")
        self.assertEqual(len(response.data["citations"]), 1)
        self.assertEqual(response.data["citations"][0]["document_name"], "python_doc.txt")

        mock_retrieve.assert_called_once_with("What is Python?", document_ids=None, top_k=5)
        mock_generate.assert_called_once()

    def test_create_chat_session(self):
        url = reverse('chat-sessions')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertEqual(ChatSession.objects.first().user, self.user)

    def test_get_chat_sessions(self):
        ChatSession.objects.create(user=self.user)
        ChatSession.objects.create(user=self.user)
        url = reverse('chat-sessions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is active, the results are under 'results'
        self.assertEqual(len(response.data['results']), 2)

    @patch('chat.views.RetrieverService.retrieve_context')
    @patch('chat.views.LLMService.generate_answer')
    def test_query_with_session_saves_messages(self, mock_generate, mock_retrieve):
        session = ChatSession.objects.create(user=self.user)
        
        mock_retrieve.return_value = []
        mock_generate.return_value = {
            "answer": "This is a test response.",
            "citations": []
        }
        
        response = self.client.post(self.query_url, {
            "query": "Hello AI",
            "session_id": session.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].role, 'USER')
        self.assertEqual(messages[0].message, 'Hello AI')
        self.assertEqual(messages[1].role, 'AI')
        self.assertEqual(messages[1].message, 'This is a test response.')

    @patch('chat.views.RetrieverService.retrieve_context')
    @patch('chat.views.LLMService.generate_answer')
    def test_query_debug_mode(self, mock_generate, mock_retrieve):
        # Mock Context Retrieval
        mock_retrieve.return_value = (
            [{"text": "Python is a programming language.", "relevance_score": 0.9, "chunk_id": "c1", "document_name": "python_doc.txt"}],
            384 # embedding dim
        )
        
        # Mock LLM Response
        mock_generate.return_value = {
            "answer": "Python is a programming language.",
            "citations": [],
            "debug_info": {
                "prompt_sent": "SYSTEM: You are helpful\nUSER: Context: ...",
                "token_count": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
            }
        }

        Document.objects.create(uploaded_by=self.user, file_name="test.txt")

        response = self.client.post(self.query_url, {"query": "What is Python?", "debug": True})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], "Python is a programming language.")
        self.assertIn("debug", response.data)
        self.assertEqual(response.data["debug"]["original_user_question"], "What is Python?")
        self.assertEqual(response.data["debug"]["generated_embedding_dimension"], 384)
        self.assertIn("response_generation_time", response.data["debug"])
        self.assertEqual(response.data["debug"]["token_count"]["total_tokens"], 15)
        
        # Test disable debug
        with self.settings(ENABLE_DEBUG_MODE=False):
            # The retriever will be called without debug since is_debug evaluates to False
            mock_retrieve.return_value = [{"text": "Python is a programming language."}]
            mock_generate.return_value = {"answer": "Python is a programming language.", "citations": []}
            
            response = self.client.post(self.query_url, {"query": "What is Python?", "debug": True})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotIn("debug", response.data)

    def test_get_chat_messages(self):
        session = ChatSession.objects.create(user=self.user)
        ChatMessage.objects.create(session=session, role='USER', message='Msg 1')
        ChatMessage.objects.create(session=session, role='AI', message='Msg 2')
        
        url = reverse('chat-messages', kwargs={'session_id': session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['message'], 'Msg 1')
        self.assertEqual(response.data['results'][1]['message'], 'Msg 2')

class ChatSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='testpassword123')
        self.user2 = User.objects.create_user(username='user2', password='testpassword123')
        
        # User 1 has a document in a collection
        self.col1 = DocumentCollection.objects.create(owner=self.user1, name="User 1 Collection")
        self.doc1 = Document.objects.create(uploaded_by=self.user1, collection=self.col1, file_name="secret1.pdf")
        
        # User 2 has a document
        self.doc2 = Document.objects.create(uploaded_by=self.user2, file_name="secret2.pdf")
        
        self.query_url = reverse('chat-query')

    @patch('chat.views.RetrieverService.retrieve_context')
    @patch('chat.views.LLMService.generate_answer')
    def test_user_cannot_access_other_user_document(self, mock_generate, mock_retrieve):
        self.client.force_authenticate(user=self.user1)
        
        # Try to query explicitly giving user2's document_id
        response = self.client.post(self.query_url, {
            "query": "What is secret 2?",
            "document_ids": [self.doc2.id] # Belongs to user2
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return 'no documents available' rather than calling retriever
        self.assertEqual(response.data['answer'], "You have no documents available to search in this context.")
        mock_retrieve.assert_not_called()

    @patch('chat.views.RetrieverService.retrieve_context')
    @patch('chat.views.LLMService.generate_answer')
    def test_user_cannot_access_other_user_collection(self, mock_generate, mock_retrieve):
        self.client.force_authenticate(user=self.user2)
        
        # Try to query explicitly giving user1's collection_id
        response = self.client.post(self.query_url, {
            "query": "What is in collection 1?",
            "collection_id": self.col1.id # Belongs to user1
        })
        
        # get_object_or_404 should return 404 since user2 doesn't own col1
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_retrieve.assert_not_called()

    @patch('chat.views.RetrieverService.retrieve_context')
    @patch('chat.views.LLMService.generate_answer')
    def test_retriever_is_bounded_by_user_documents(self, mock_generate, mock_retrieve):
        self.client.force_authenticate(user=self.user1)
        
        mock_retrieve.return_value = []
        mock_generate.return_value = {"answer": "Some answer", "citations": []}
        
        # Just a normal query
        response = self.client.post(self.query_url, {
            "query": "What is secret 1?"
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Retriever must have been called specifically with user1's document_ids
        mock_retrieve.assert_called_once_with("What is secret 1?", document_ids=[self.doc1.id], top_k=5)

