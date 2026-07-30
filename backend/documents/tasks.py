import logging
from celery import shared_task
from django.db import transaction
from .models import Document
from .processing import DocumentProcessingService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=5, autoretry_for=(Exception,), retry_backoff=True)
def process_document_task(self, document_id):
    logger.info(f"Task process_document_task started for document_id={document_id}")
    
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document with id {document_id} does not exist.")
        return {'status': 'failed', 'error': 'Document not found'}

    # Idempotent processing: prevent processing if already COMPLETED or currently PROCESSING
    if document.processing_status == 'COMPLETED':
        logger.info(f"Document {document_id} is already processed.")
        return {'status': 'completed', 'document_id': document_id}
    
    # Store task id
    # We can use Celery task state, but we also can update the document directly.
    # We don't have a task_id field on Document model yet. The user wants the upload endpoint to return document id, task id, initial status. We can just return the task id from the endpoint, and provide an endpoint to check status.
    
    try:
        # We can call the original service which handles extract -> chunk -> embed
        DocumentProcessingService.process_document(document_id)
        
        # After it's done, we check if it failed inside the service
        document.refresh_from_db()
        if document.processing_status == 'FAILED':
            raise Exception("Document processing failed inside service.")
            
        return {'status': 'completed', 'document_id': document_id}
    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {exc}")
        document.processing_status = 'FAILED'
        document.save(update_fields=['processing_status'])
        # Re-raise to trigger Celery retry
        raise self.retry(exc=exc)
