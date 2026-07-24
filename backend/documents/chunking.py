import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .models import Document, DocumentChunk
from ai_engine.embeddings import EmbeddingService

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
        created_chunks = DocumentChunk.objects.bulk_create(document_chunks)
        
        logger.info(f"Created {len(document_chunks)} chunks for document {document.id}. Starting embedding process...")

        # Store in Vector DB
        try:
            embedding_service = EmbeddingService()
            # Fetch the chunks back to have primary keys assigned (bulk_create might not set PKs in some DBs)
            saved_chunks = DocumentChunk.objects.filter(document=document)
            success = embedding_service.embed_and_store_chunks(saved_chunks)
            if success:
                logger.info(f"Successfully embedded and stored {len(saved_chunks)} chunks in ChromaDB.")
            else:
                logger.error("Failed to store embeddings in ChromaDB.")
        except Exception as e:
            logger.error(f"Embedding pipeline failed: {e}", exc_info=True)

        return True
