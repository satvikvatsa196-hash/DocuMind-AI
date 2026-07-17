from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Document, DocumentCollection
from .serializers import DocumentSerializer, DocumentCollectionSerializer
from .services import DocumentService

class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)

class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        collection_id = request.data.get('collection_id')

        try:
            document = DocumentService.process_upload(
                user=request.user,
                file=file,
                collection_id=collection_id
            )
            serializer = DocumentSerializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DjangoValidationError as e:
            return Response({"error": str(e.message) if hasattr(e, 'message') else str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An error occurred during file upload.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentCollectionListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DocumentCollection.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
