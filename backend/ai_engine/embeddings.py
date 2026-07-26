import logging
import uuid
import chromadb
from django.conf import settings
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # Initialize the embedding model. This abstraction allows us to swap 
        # to OpenAIEmbeddings or Gemini later if needed.
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Initialize ChromaDB client. In production, this would connect to the 
        # remote ChromaDB instance.
        try:
            # Parse host and port from CHROMA_DB_URL, assuming http://host:port
            url_parts = settings.CHROMA_DB_URL.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 8000
            
            self.chroma_client = chromadb.HttpClient(host=host, port=port)
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_DB_COLLECTION,
                metadata={"hnsw:space": "cosine"} # Default cosine similarity
            )
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            self.chroma_client = None
            self.collection = None

    def embed_and_store_chunks(self, document_chunks):
        """
        Takes a list of DocumentChunk objects, generates embeddings, 
        and stores them in ChromaDB with associated metadata.
        """
        if not self.collection:
            logger.error("ChromaDB collection is not initialized. Cannot store chunks.")
            return False

        if not document_chunks:
            return True

        texts = []
        metadatas = []
        ids = []

        for chunk in document_chunks:
            texts.append(chunk.chunk_text)
            
            # Prepare metadata mapping. ChromaDB requires flat dicts with string/int/float values.
            metadata = {
                "chunk_id": chunk.id,
                "document_id": chunk.document.id,
                "document_name": chunk.document.file_name,
                "chunk_number": chunk.chunk_number,
                "page_number": chunk.page_number if chunk.page_number is not None else -1,
            }
            # Append any existing metadata from the chunk
            if isinstance(chunk.metadata, dict):
                for k, v in chunk.metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        metadata[k] = v
            
            metadatas.append(metadata)
            
            # Generate a unique ID for the vector
            ids.append(f"doc_{chunk.document.id}_chunk_{chunk.id}_{uuid.uuid4().hex[:8]}")

        try:
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = self.embedding_model.embed_documents(texts)
            
            logger.info("Storing embeddings in ChromaDB...")
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info("Successfully stored embeddings.")
            return True
        except Exception as e:
            logger.error(f"Failed to embed and store chunks: {e}", exc_info=True)
            return False

    def retrieve_similar_chunks(self, query, top_k=5, document_ids=None, is_debug=False):
        """
        Retrieves the most similar chunks for a given query.
        Optionally filter by a list of document_ids.
        """
        if not self.collection:
            logger.error("ChromaDB collection is not initialized. Cannot retrieve chunks.")
            if is_debug:
                return [], 0
            return []

        try:
            query_embedding = self.embedding_model.embed_query(query)
            embedding_dim = len(query_embedding)
            
            # Prepare where clause for filtering by document_ids
            where_clause = None
            if document_ids:
                if len(document_ids) == 1:
                    where_clause = {"document_id": document_ids[0]}
                else:
                    where_clause = {"document_id": {"$in": document_ids}}

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause
            )
            
            # Format the output for easy consumption
            formatted_results = []
            if results and 'documents' in results and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    # ChromaDB distance using cosine space is 1 - cosine similarity
                    distance = results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    formatted_results.append({
                        "text": results['documents'][0][i],
                        "metadata": metadata,
                        "distance": distance,
                        "id": results['ids'][0][i],
                        "relevance_score": 1.0 - distance,
                        "document_name": metadata.get("document_name", "Unknown Document"),
                        "page_number": metadata.get("page_number", -1),
                        "chunk_id": metadata.get("chunk_id", -1)
                    })
                    
            if is_debug:
                return formatted_results, embedding_dim
            return formatted_results
        except Exception as e:
            logger.error(f"Error retrieving similar chunks: {e}", exc_info=True)
            if is_debug:
                return [], 0
            return []
