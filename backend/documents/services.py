import os
from django.core.exceptions import ValidationError
from .models import Document, DocumentCollection
import threading
from .processing import DocumentProcessingService

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

class DocumentService:
    @staticmethod
    def validate_file(file):
        # Check file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"Unsupported file type. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Check file size
        if file.size > MAX_FILE_SIZE_BYTES:
            raise ValidationError(f"File size exceeds the {MAX_FILE_SIZE_MB}MB limit.")

    @staticmethod
    def process_upload(user, file, collection_id=None):
        DocumentService.validate_file(file)

        collection = None
        if collection_id:
            collection = DocumentCollection.objects.filter(id=collection_id, owner=user).first()
            if not collection:
                raise ValidationError("Collection not found or you do not have permission to access it.")

        ext = os.path.splitext(file.name)[1].lower().replace('.', '')

        document = Document(
            uploaded_by=user,
            collection=collection,
            file_name=file.name,
            file_type=ext,
            file_path=file,
            processing_status='UPLOADING'
        )
        document.save()

        # Start text extraction in the background
        thread = threading.Thread(target=DocumentProcessingService.process_document, args=(document.id,))
        thread.daemon = True
        thread.start()

        return document
