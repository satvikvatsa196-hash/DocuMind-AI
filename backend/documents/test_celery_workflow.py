import json
import os
from django.test import TestCase
from django.contrib.auth import get_user_model
from fastapi.testclient import TestClient
from config.asgi import application
import jwt
from django.conf import settings
from .models import Document
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class CeleryWorkflowIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser_celery", password="testpassword")
        self.client = TestClient(application)
        
        payload = {"user_id": self.user.id}
        self.token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @patch('documents.tasks.process_document_task.delay')
    def test_upload_starts_celery_task(self, mock_delay):
        class MockTask:
            id = "test_celery_task_id"
        mock_delay.return_value = MockTask()
        
        # Test document upload
        file_content = b"This is a test document."
        files = {"file": ("test_doc.txt", file_content, "text/plain")}
        
        response = self.client.post("/api/dashboard/documents/upload", headers=self.headers, files=files)
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        self.assertIn("id", data)
        self.assertEqual(data["task_id"], "test_celery_task_id")
        self.assertEqual(data["processing_status"], "UPLOADING")
        
        doc = Document.objects.get(id=data["id"])
        self.assertEqual(doc.task_id, "test_celery_task_id")
        
        mock_delay.assert_called_once_with(doc.id)

    @patch('celery.result.AsyncResult')
    def test_get_task_status(self, mock_async_result):
        mock_result_instance = MagicMock()
        mock_result_instance.status = "PROCESSING"
        mock_result_instance.state = "PROCESSING"
        mock_async_result.return_value = mock_result_instance
        
        response = self.client.get("/api/dashboard/documents/task/test_task_123/status", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["task_id"], "test_task_123")
        self.assertEqual(data["status"], "PROCESSING")

    @patch('config.celery.app.control.revoke')
    def test_cancel_task(self, mock_revoke):
        doc = Document.objects.create(
            uploaded_by=self.user,
            file_name="cancel_doc.txt",
            file_type="txt",
            processing_status="UPLOADING",
            task_id="task_to_cancel"
        )
        
        response = self.client.post("/api/dashboard/documents/task/task_to_cancel/cancel", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "CANCELLED")
        
        mock_revoke.assert_called_once_with("task_to_cancel", terminate=True)
        
        doc.refresh_from_db()
        self.assertEqual(doc.processing_status, "FAILED")

    @patch('documents.processing.DocumentProcessingService.process_document')
    def test_celery_task_execution(self, mock_process_document):
        from documents.tasks import process_document_task
        
        doc = Document.objects.create(
            uploaded_by=self.user,
            file_name="task_doc.txt",
            file_type="txt",
            processing_status="UPLOADING"
        )
        
        # Execute task synchronously
        result = process_document_task(doc.id)
        
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["document_id"], doc.id)
        
        mock_process_document.assert_called_once_with(doc.id)

    def test_celery_task_idempotency(self):
        from documents.tasks import process_document_task
        
        doc = Document.objects.create(
            uploaded_by=self.user,
            file_name="idempotent_doc.txt",
            file_type="txt",
            processing_status="COMPLETED"
        )
        
        with patch('documents.processing.DocumentProcessingService.process_document') as mock_process:
            result = process_document_task(doc.id)
            
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["document_id"], doc.id)
            # Should not call process_document if already completed
            mock_process.assert_not_called()
