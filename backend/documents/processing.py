import logging
import fitz  # PyMuPDF
import docx
from django.utils import timezone
from .models import Document
from .chunking import ChunkingService

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
                extracted_text, ocr_stats = DocumentProcessingService._extract_pdf(document.file_path.path)
                document.has_ocr_text = ocr_stats.get('has_ocr', False)
                document.ocr_confidence = ocr_stats.get('confidence')
                document.ocr_processing_time = ocr_stats.get('processing_time')
            elif document.file_type == 'docx':
                extracted_text = DocumentProcessingService._extract_docx(document.file_path.path)
            elif document.file_type == 'txt':
                extracted_text = DocumentProcessingService._extract_txt(document.file_path.path)
            else:
                raise ValueError(f"Unsupported file type for extraction: {document.file_type}")

            # Save the extracted text
            document.extracted_text = extracted_text
            document.processing_status = 'COMPLETED'
            
            update_fields = ['extracted_text', 'processing_status']
            if document.file_type == 'pdf':
                update_fields.extend(['has_ocr_text', 'ocr_confidence', 'ocr_processing_time'])
                
            document.save(update_fields=update_fields)
            logger.info(f"Successfully processed document {document.id}")

            # Trigger chunking
            ChunkingService.chunk_document(document.id)

        except Exception as e:
            logger.error(f"Failed to process document {document.id}: {str(e)}", exc_info=True)
            document.processing_status = 'FAILED'
            document.save(update_fields=['processing_status'])

    @staticmethod
    def _extract_pdf(file_path):
        from django.conf import settings
        import time
        import numpy as np
        
        enable_ocr = getattr(settings, 'ENABLE_OCR', True)
        
        text = ""
        ocr_confidence_sum = 0
        ocr_page_count = 0
        has_ocr = False
        start_time = time.time()
        
        paddle_ocr = None
        
        try:
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    page_text = page.get_text().strip()
                    
                    if not page_text and enable_ocr:
                        try:
                            if paddle_ocr is None:
                                from paddleocr import PaddleOCR
                                paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                                
                            pix = page.get_pixmap(dpi=150)
                            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                            
                            if pix.n == 4:
                                import cv2
                                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                            elif pix.n == 1:
                                import cv2
                                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                            elif pix.n == 3:
                                import cv2
                                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                                
                            result = paddle_ocr.ocr(img, cls=True)
                            
                            page_ocr_text = ""
                            page_conf_sum = 0
                            word_count = 0
                            
                            if result and result[0]:
                                for line in result[0]:
                                    if line:
                                        page_ocr_text += line[1][0] + " "
                                        page_conf_sum += line[1][1]
                                        word_count += 1
                                        
                            if word_count > 0:
                                page_text = page_ocr_text.strip()
                                ocr_confidence_sum += (page_conf_sum / word_count)
                                ocr_page_count += 1
                                has_ocr = True
                                
                        except Exception as ocr_e:
                            logger.error(f"OCR failed on page {page_num} of {file_path}: {str(ocr_e)}")
                            
                    # Add marker for ChunkingService to preserve page numbers
                    if page_text:
                        text += f"--- PAGE {page_num} ---\n{page_text}\n\n"
                        
        except Exception as e:
            logger.error(f"Error extracting PDF from {file_path}: {str(e)}")
            raise
            
        ocr_stats = {
            'has_ocr': has_ocr,
            'confidence': ocr_confidence_sum / ocr_page_count if ocr_page_count > 0 else None,
            'processing_time': time.time() - start_time if has_ocr else 0.0
        }
        
        return text.strip(), ocr_stats

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
