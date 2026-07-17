import logging
import fitz  # PyMuPDF
import docx
from django.utils import timezone
from .models import Document

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    @staticmethod
    def process_document(document_id):
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            logger.error(f"Document with id {document_id} does not exist.")
            return

        logger.info(f"Starting processing for document {document.id} ({document.file_name})")
        
        # Update status to PROCESSING
        document.processing_status = 'PROCESSING'
        document.save(update_fields=['processing_status'])

        extracted_text = ""

        try:
            # File extraction logic based on extension
            if document.file_type == 'pdf':
                extracted_text = DocumentProcessingService._extract_pdf(document.file_path.path)
            elif document.file_type == 'docx':
                extracted_text = DocumentProcessingService._extract_docx(document.file_path.path)
            elif document.file_type == 'txt':
                extracted_text = DocumentProcessingService._extract_txt(document.file_path.path)
            else:
                raise ValueError(f"Unsupported file type for extraction: {document.file_type}")

            # Save the extracted text
            document.extracted_text = extracted_text
            document.processing_status = 'COMPLETED'
            document.save(update_fields=['extracted_text', 'processing_status'])
            logger.info(f"Successfully processed document {document.id}")

        except Exception as e:
            logger.error(f"Failed to process document {document.id}: {str(e)}", exc_info=True)
            document.processing_status = 'FAILED'
            document.save(update_fields=['processing_status'])

    @staticmethod
    def _extract_pdf(file_path):
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting PDF from {file_path}: {str(e)}")
            raise
        return text.strip()

    @staticmethod
    def _extract_docx(file_path):
        text = ""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error extracting DOCX from {file_path}: {str(e)}")
            raise
        return text.strip()

    @staticmethod
    def _extract_txt(file_path):
        text = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            # Fallback to standard encoding if utf-8 fails
            with open(file_path, 'r', encoding='ISO-8859-1') as f:
                text = f.read()
        except Exception as e:
            logger.error(f"Error extracting TXT from {file_path}: {str(e)}")
            raise
        return text.strip()
