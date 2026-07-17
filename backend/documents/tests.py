import io
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Document, DocumentCollection

User = get_user_model()

class DocumentUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        self.client.force_authenticate(user=self.user)
        self.upload_url = reverse('document-upload')
        self.list_url = reverse('document-list')
        
    def test_upload_supported_file(self):
        file = SimpleUploadedFile("test.txt", b"This is a test text file.", content_type="text/plain")
        response = self.client.post(self.upload_url, {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.first()
        self.assertEqual(doc.file_name, "test.txt")
        self.assertEqual(doc.file_type, "txt")
        self.assertEqual(doc.processing_status, "PENDING")
        self.assertEqual(doc.uploaded_by, self.user)

    def test_upload_unsupported_file(self):
        file = SimpleUploadedFile("test.csv", b"a,b,c", content_type="text/csv")
        response = self.client.post(self.upload_url, {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(Document.objects.count(), 0)

    def test_upload_file_exceeds_size(self):
        # Create a file slightly larger than 10MB
        large_content = b"0" * (10 * 1024 * 1024 + 1)
        file = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")
        response = self.client.post(self.upload_url, {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(Document.objects.count(), 0)

    def test_list_documents(self):
        file = SimpleUploadedFile("test.pdf", b"%PDF-1.4...", content_type="application/pdf")
        self.client.post(self.upload_url, {'file': file}, format='multipart')
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['file_name'], "test.pdf")

    def test_upload_with_collection(self):
        collection = DocumentCollection.objects.create(owner=self.user, name="My Documents")
        file = SimpleUploadedFile("test.docx", b"PK...", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        response = self.client.post(self.upload_url, {'file': file, 'collection_id': collection.id}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.first()
        self.assertEqual(doc.collection, collection)
