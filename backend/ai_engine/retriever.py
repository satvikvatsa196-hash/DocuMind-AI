from .embeddings import EmbeddingService

class RetrieverService:
    @staticmethod
    def retrieve_context(query, document_ids=None, top_k=5, is_debug=False):
        embedding_service = EmbeddingService()
        return embedding_service.retrieve_similar_chunks(query, top_k=top_k, document_ids=document_ids, is_debug=is_debug)
