from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
import math

from .models import Document
from django.contrib.auth import get_user_model
from chat.fastapi_stream import get_current_user

router = APIRouter(prefix="/dashboard/documents", tags=["Dashboard Documents"])

class DocumentDTO(BaseModel):
    id: int
    filename: str = Field(alias="file_name")
    upload_timestamp: datetime = Field(alias="uploaded_at")
    processing_status: str
    page_count: Optional[int] = 0
    chunk_count: Optional[int] = 0
    embedding_status: Optional[str] = "PENDING"
    processing_duration: Optional[float] = 0.0
    embedding_model: Optional[str] = "text-embedding-ada-002"
    vector_database_status: Optional[str] = "PENDING"

    class Config:
        from_attributes = True
        populate_by_name = True

class PaginatedDocumentResponse(BaseModel):
    items: List[DocumentDTO]
    total: int
    page: int
    size: int
    pages: int

@router.get("/", response_model=PaginatedDocumentResponse)
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user=Depends(get_current_user)
):
    async def fetch_docs():
        qs = Document.objects.filter(uploaded_by=user).order_by('-uploaded_at')
        if status_filter:
            qs = qs.filter(processing_status=status_filter.upper())
            
        total = await qs.acount()
        pages = math.ceil(total / size) if total > 0 else 1
        
        offset = (page - 1) * size
        docs = await sync_to_async(list)(qs[offset:offset + size])
        return docs, total, pages

    docs, total, pages = await fetch_docs()
    
    return PaginatedDocumentResponse(
        items=[DocumentDTO.model_validate(doc) for doc in docs],
        total=total,
        page=page,
        size=size,
        pages=pages
    )

@router.get("/{doc_id}", response_model=DocumentDTO)
async def get_document(doc_id: int, user=Depends(get_current_user)):
    try:
        doc = await Document.objects.aget(id=doc_id, uploaded_by=user)
        return DocumentDTO.model_validate(doc)
    except Document.DoesNotExist:
        raise HTTPException(status_code=404, detail="Document not found")

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: int, user=Depends(get_current_user)):
    try:
        doc = await Document.objects.aget(id=doc_id, uploaded_by=user)
        await sync_to_async(doc.delete)()
        return None
    except Document.DoesNotExist:
        raise HTTPException(status_code=404, detail="Document not found")

@router.post("/{doc_id}/retry", response_model=DocumentDTO)
async def retry_processing(doc_id: int, user=Depends(get_current_user)):
    try:
        doc = await Document.objects.aget(id=doc_id, uploaded_by=user)
        
        if doc.processing_status not in ['FAILED', 'COMPLETED']:
            raise HTTPException(status_code=400, detail="Can only retry FAILED or COMPLETED documents.")
            
        doc.processing_status = 'UPLOADING'
        doc.extracted_text = None
        doc.chunk_count = 0
        doc.page_count = 0
        doc.embedding_status = 'PENDING'
        doc.vector_database_status = 'PENDING'
        doc.processing_duration = 0.0
        await sync_to_async(doc.save)()
        
        # Start background processing
        from documents.processing import DocumentProcessingService
        import threading
        thread = threading.Thread(target=DocumentProcessingService.process_document, args=(doc.id,))
        thread.daemon = True
        thread.start()
        
        return DocumentDTO.model_validate(doc)
    except Document.DoesNotExist:
        raise HTTPException(status_code=404, detail="Document not found")
