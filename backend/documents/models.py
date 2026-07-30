from django.db import models
from django.conf import settings

class DocumentCollection(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Document(models.Model):
    PROCESSING_STATUS_CHOICES = (
        ('UPLOADING', 'Uploading'),
        ('EXTRACTING', 'Extracting'),
        ('CHUNKING', 'Chunking'),
        ('EMBEDDING', 'Embedding'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    collection = models.ForeignKey(DocumentCollection, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_path = models.FileField(upload_to='documents/%Y/%m/%d/')
    extracted_text = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='UPLOADING')
    page_count = models.IntegerField(default=0, null=True, blank=True)
    chunk_count = models.IntegerField(default=0, null=True, blank=True)
    embedding_status = models.CharField(max_length=50, default='PENDING', null=True, blank=True)
    processing_duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds")
    embedding_model = models.CharField(max_length=100, default='text-embedding-ada-002', null=True, blank=True)
    vector_database_status = models.CharField(max_length=50, default='PENDING', null=True, blank=True)
    task_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.file_name

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_text = models.TextField()
    chunk_number = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.document.file_name} - Chunk {self.chunk_number}"

