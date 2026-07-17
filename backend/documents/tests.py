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

from unittest.mock import patch
from .processing import DocumentProcessingService

class DocumentProcessingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='processor', password='testpassword123')
        
    @patch('documents.processing.DocumentProcessingService._extract_txt')
    def test_process_txt_document(self, mock_extract_txt):
        mock_extract_txt.return_value = "Mocked TXT content"
        file = SimpleUploadedFile("test.txt", b"Mocked TXT content", content_type="text/plain")
        document = Document.objects.create(
            uploaded_by=self.user,
            file_name="test.txt",
            file_type="txt",
            file_path=file,
            processing_status="PENDING"
        )
        
        DocumentProcessingService.process_document(document.id)
        document.refresh_from_db()
        
        self.assertEqual(document.processing_status, "COMPLETED")
        self.assertEqual(document.extracted_text, "Mocked TXT content")

    @patch('documents.processing.DocumentProcessingService._extract_pdf')
    def test_process_pdf_document(self, mock_extract_pdf):
        mock_extract_pdf.return_value = "Mocked PDF content"
        file = SimpleUploadedFile("test.pdf", b"dummy pdf", content_type="application/pdf")
        document = Document.objects.create(
            uploaded_by=self.user,
            file_name="test.pdf",
            file_type="pdf",
            file_path=file,
            processing_status="PENDING"
        )
        
        DocumentProcessingService.process_document(document.id)
        document.refresh_from_db()
        
        self.assertEqual(document.processing_status, "COMPLETED")
        self.assertEqual(document.extracted_text, "Mocked PDF content")

    @patch('documents.processing.DocumentProcessingService._extract_docx')
    def test_process_docx_document(self, mock_extract_docx):
        mock_extract_docx.return_value = "Mocked DOCX content"
        file = SimpleUploadedFile("test.docx", b"dummy docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        document = Document.objects.create(
            uploaded_by=self.user,
            file_name="test.docx",
            file_type="docx",
            file_path=file,
            processing_status="PENDING"
        )
        
        DocumentProcessingService.process_document(document.id)
        document.refresh_from_db()
        
        self.assertEqual(document.processing_status, "COMPLETED")
        self.assertEqual(document.extracted_text, "Mocked DOCX content")

    @patch('documents.processing.DocumentProcessingService._extract_txt')
    def test_process_document_failure(self, mock_extract_txt):
        mock_extract_txt.side_effect = Exception("Simulated extraction error")
        file = SimpleUploadedFile("test.txt", b"Mocked TXT content", content_type="text/plain")
        document = Document.objects.create(
            uploaded_by=self.user,
            file_name="test.txt",
            file_type="txt",
            file_path=file,
            processing_status="PENDING"
        )
        
        DocumentProcessingService.process_document(document.id)
        document.refresh_from_db()
        
        self.assertEqual(document.processing_status, "FAILED")
        self.assertIsNone(document.extracted_text)

from .chunking import ChunkingService
from .models import DocumentChunk

class ChunkingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='chunker', password='testpassword123')
        self.document = Document.objects.create(
            uploaded_by=self.user,
            file_name="long_doc.txt",
            file_type="txt",
            extracted_text="A" * 2500, # 2500 characters
            processing_status="COMPLETED"
        )

    def test_chunk_document_success(self):
        # Chunk size 1000, overlap 200
        # Chunks: 
        # 1: 0 to 1000
        # 2: 800 to 1800
        # 3: 1600 to 2500 (900 chars)
        result = ChunkingService.chunk_document(self.document.id, chunk_size=1000, chunk_overlap=200)
        self.assertTrue(result)
        
        chunks = DocumentChunk.objects.filter(document=self.document).order_by('chunk_number')
        self.assertEqual(chunks.count(), 3)
        
        self.assertEqual(len(chunks[0].chunk_text), 1000)
        self.assertEqual(len(chunks[1].chunk_text), 1000)
        self.assertEqual(len(chunks[2].chunk_text), 900)
        
        self.assertEqual(chunks[0].chunk_number, 1)
        self.assertEqual(chunks[0].metadata['source'], 'long_doc.txt')
        self.assertEqual(chunks[0].metadata['document_id'], self.document.id)

    def test_chunk_document_no_text(self):
        doc_no_text = Document.objects.create(
            uploaded_by=self.user,
            file_name="empty.txt",
            file_type="txt",
            extracted_text=""
        )
        result = ChunkingService.chunk_document(doc_no_text.id)
        self.assertFalse(result)
        self.assertEqual(DocumentChunk.objects.filter(document=doc_no_text).count(), 0)

    def test_chunk_document_not_found(self):
        result = ChunkingService.chunk_document(9999)
        self.assertFalse(result)
