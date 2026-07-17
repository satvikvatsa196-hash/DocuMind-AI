import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import Document, DocumentChunk

logger = logging.getLogger(__name__)

class ChunkingService:
    @staticmethod
    def chunk_document(document_id, chunk_size=1000, chunk_overlap=200):
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            logger.error(f"Document with id {document_id} not found for chunking.")
            return False

        if not document.extracted_text:
            logger.warning(f"Document {document.id} has no extracted text to chunk.")
            return False
            
        logger.info(f"Chunking document {document.id} with size={chunk_size}, overlap={chunk_overlap}")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        # Clear existing chunks if re-chunking
        DocumentChunk.objects.filter(document=document).delete()

        chunks = text_splitter.split_text(document.extracted_text)
        
        document_chunks = []
        for i, chunk_text in enumerate(chunks, start=1):
            metadata = {
                "source": document.file_name,
                "document_id": document.id,
                "file_type": document.file_type,
            }
            if document.collection:
                metadata["collection_id"] = document.collection.id

            document_chunks.append(
                DocumentChunk(
                    document=document,
                    chunk_text=chunk_text,
                    chunk_number=i,
                    page_number=None, # Page numbers require parsing modifications to extract page by page
                    metadata=metadata
                )
            )

        # Bulk create chunks for efficiency
        DocumentChunk.objects.bulk_create(document_chunks)
        
        logger.info(f"Created {len(document_chunks)} chunks for document {document.id}")
        return True
