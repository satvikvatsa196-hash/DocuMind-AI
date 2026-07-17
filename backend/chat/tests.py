import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

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
