from rest_framework import serializers
from .models import Document, DocumentCollection

class DocumentCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCollection
        fields = ('id', 'name', 'description', 'created_at')
        read_only_fields = ('id', 'created_at')

class DocumentSerializer(serializers.ModelSerializer):
    collection_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Document
        fields = ('id', 'collection', 'collection_id', 'file_name', 'file_type', 'file_path', 'uploaded_at', 'processing_status', 'file')
        read_only_fields = ('id', 'collection', 'file_name', 'file_type', 'file_path', 'uploaded_at', 'processing_status')
