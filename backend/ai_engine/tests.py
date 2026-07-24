from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from documents.models import Document, DocumentChunk
from .embeddings import EmbeddingService

User = get_user_model()

class EmbeddingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='embedder', password='testpassword123')
        self.document = Document.objects.create(
            uploaded_by=self.user,
            file_name="test_embed.pdf",
            file_type="pdf",
            extracted_text="Some text here"
        )
        self.chunk1 = DocumentChunk.objects.create(
            document=self.document,
            chunk_text="This is the first chunk of text.",
            chunk_number=1,
            page_number=1
        )
        self.chunk2 = DocumentChunk.objects.create(
            document=self.document,
            chunk_text="This is the second chunk of text.",
            chunk_number=2,
            page_number=2
        )

    @patch('ai_engine.embeddings.chromadb.HttpClient')
    @patch('ai_engine.embeddings.HuggingFaceEmbeddings')
    def test_embed_and_store_chunks(self, MockHuggingFace, MockChromaClient):
        # Mock Chroma Client and Collection
        mock_collection = MagicMock()
        mock_client_instance = MockChromaClient.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock Embeddings
        mock_embedding_instance = MockHuggingFace.return_value
        mock_embedding_instance.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        service = EmbeddingService()
        success = service.embed_and_store_chunks([self.chunk1, self.chunk2])
        
        self.assertTrue(success)
        mock_embedding_instance.embed_documents.assert_called_once_with([self.chunk1.chunk_text, self.chunk2.chunk_text])
        self.assertEqual(mock_collection.add.call_count, 1)

    @patch('ai_engine.embeddings.chromadb.HttpClient')
    @patch('ai_engine.embeddings.HuggingFaceEmbeddings')
    def test_retrieve_similar_chunks(self, MockHuggingFace, MockChromaClient):
        # Mock Chroma Client and Collection
        mock_collection = MagicMock()
        mock_client_instance = MockChromaClient.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Setup mock retrieval results
        mock_collection.query.return_value = {
            'documents': [['This is the first chunk of text.']],
            'metadatas': [[{
                'document_id': self.document.id, 
                'document_name': self.document.file_name,
                'page_number': 1,
                'chunk_id': self.chunk1.id
            }]],
            'distances': [[0.05]],
            'ids': [['doc_1_chunk_1_abc']]
        }
        
        # Mock Embeddings
        mock_embedding_instance = MockHuggingFace.return_value
        mock_embedding_instance.embed_query.return_value = [0.1, 0.2]
        
        service = EmbeddingService()
        results = service.retrieve_similar_chunks("first chunk", top_k=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], 'This is the first chunk of text.')
        self.assertEqual(results[0]['document_name'], 'test_embed.pdf')
        self.assertEqual(results[0]['page_number'], 1)
        self.assertEqual(results[0]['chunk_id'], self.chunk1.id)
        self.assertAlmostEqual(results[0]['relevance_score'], 0.95)
        mock_collection.query.assert_called_once()

from ai_engine.llm import LLMService

class LLMServiceTests(TestCase):
    @patch('ai_engine.llm.ChatOpenAI')
    def test_generate_answer_citations(self, MockChatOpenAI):
        # Setup mock response
        mock_llm_instance = MockChatOpenAI.return_value
        mock_response = MagicMock()
        mock_response.content = '''
        {
          "answer": "This is the generated answer.",
          "citations": [
            {
              "document_name": "test_embed.pdf",
              "page_number": 1,
              "chunk_id": "123"
            }
          ]
        }
        '''
        mock_llm_instance.invoke.return_value = mock_response

        service = LLMService()
        
        # Fake chunks list matching retrieve_similar_chunks output
        context_chunks = [
            {
                "text": "This is the first chunk of text.",
                "document_name": "test_embed.pdf",
                "page_number": 1,
                "chunk_id": 123,
                "relevance_score": 0.95
            },
            {
                "text": "Irrelevant chunk.",
                "document_name": "test_embed.pdf",
                "page_number": 2,
                "chunk_id": 124,
                "relevance_score": 0.8
            }
        ]

        result = service.generate_answer("test query?", context_chunks)
        
        self.assertEqual(result["answer"], "This is the generated answer.")
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["chunk_id"], "123")
        self.assertEqual(len(result["retrieved_passages"]), 1)
        
        # Verify retrieved passages contains expected chunk
        passage = result["retrieved_passages"][0]
        self.assertEqual(passage["chunk_id"], 123)
        self.assertEqual(passage["document_name"], "test_embed.pdf")
        self.assertEqual(passage["page_number"], 1)
        self.assertEqual(passage["chunk_text"], "This is the first chunk of text.")
        self.assertEqual(passage["relevance_score"], 0.95)
