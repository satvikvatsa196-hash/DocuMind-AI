import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from fastapi.testclient import TestClient
from config.asgi import application
import jwt
from django.conf import settings
from .models import Document
from unittest.mock import patch

User = get_user_model()

class DocumentDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser_dash", password="testpassword")
        self.client = TestClient(application)
        
        payload = {"user_id": self.user.id}
        self.token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create some test documents
        self.doc1 = Document.objects.create(
            uploaded_by=self.user,
            file_name="doc1.pdf",
            file_type="pdf",
            processing_status="UPLOADING",
            page_count=5,
            chunk_count=10
        )
        self.doc2 = Document.objects.create(
            uploaded_by=self.user,
            file_name="doc2.txt",
            file_type="txt",
            processing_status="COMPLETED",
            page_count=1,
            chunk_count=2,
            embedding_status="COMPLETED",
            processing_duration=1.5
        )
        self.doc3 = Document.objects.create(
            uploaded_by=self.user,
            file_name="doc3.docx",
            file_type="docx",
            processing_status="FAILED",
        )

    def test_list_documents(self):
        response = self.client.get("/api/dashboard/documents/", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 3)
        # Check order (newest first, doc3 is the newest created in setUp)
        self.assertEqual(data["items"][0]["file_name"], "doc3.docx")

    def test_list_documents_with_status_filter(self):
        response = self.client.get("/api/dashboard/documents/?status=completed", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["file_name"], "doc2.txt")

    def test_get_document(self):
        response = self.client.get(f"/api/dashboard/documents/{self.doc2.id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["file_name"], "doc2.txt")
        self.assertEqual(data["processing_status"], "COMPLETED")
        self.assertEqual(data["page_count"], 1)

    def test_delete_document(self):
        response = self.client.delete(f"/api/dashboard/documents/{self.doc1.id}", headers=self.headers)
        self.assertEqual(response.status_code, 204)
        
        # Verify it's deleted
        with self.assertRaises(Document.DoesNotExist):
            Document.objects.get(id=self.doc1.id)

    def test_retry_processing_failed(self):
        with patch('threading.Thread.start') as mock_thread:
            response = self.client.post(f"/api/dashboard/documents/{self.doc3.id}/retry", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data["processing_status"], "UPLOADING")
            
            self.doc3.refresh_from_db()
            self.assertEqual(self.doc3.processing_status, "UPLOADING")
            mock_thread.assert_called_once()

    def test_retry_processing_uploading(self):
        # Cannot retry if already uploading
        response = self.client.post(f"/api/dashboard/documents/{self.doc1.id}/retry", headers=self.headers)
        self.assertEqual(response.status_code, 400)
