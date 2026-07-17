from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from ai_engine.retriever import RetrieverService
from ai_engine.llm import LLMService

class QueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        query = request.data.get("query")
        document_ids = request.data.get("document_ids", None)
        
        if not query:
            return Response({"error": "Query is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Retrieve Context
        context_chunks = RetrieverService.retrieve_context(query, document_ids=document_ids, top_k=5)
        
        # 2. Call LLM
        llm_service = LLMService()
        response_data = llm_service.generate_answer(query, context_chunks)
        
        return Response(response_data, status=status.HTTP_200_OK)
