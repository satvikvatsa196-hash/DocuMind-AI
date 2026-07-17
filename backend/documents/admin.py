from django.contrib import admin
from .models import DocumentCollection, Document, DocumentChunk

@admin.register(DocumentCollection)
class DocumentCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'owner__username')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'uploaded_by', 'collection', 'processing_status', 'uploaded_at')
    list_filter = ('processing_status', 'file_type')
    search_fields = ('file_name', 'uploaded_by__username')

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'chunk_number', 'page_number')
    search_fields = ('document__file_name', 'chunk_text')

