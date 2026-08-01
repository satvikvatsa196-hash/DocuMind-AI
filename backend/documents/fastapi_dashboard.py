from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
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
    task_id: Optional[str] = None
    has_ocr_text: Optional[bool] = False
    ocr_confidence: Optional[float] = None
    ocr_processing_time: Optional[float] = None

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
        
        from documents.tasks import process_document_task
        task = process_document_task.delay(doc.id)
        doc.task_id = task.id
        
        await sync_to_async(doc.save)()
        
        return DocumentDTO.model_validate(doc)
    except Document.DoesNotExist:
        raise HTTPException(status_code=404, detail="Document not found")

@router.post("/upload", response_model=DocumentDTO, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    collection_id: Optional[int] = Form(None),
    user=Depends(get_current_user)
):
    from documents.services import DocumentService
    
    # Save the file temporarily to pass to Django's FileField
    temp_dir = os.path.join(os.environ.get('TEMP', '/tmp'), 'documind_uploads')
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        from django.core.files import File as DjangoFile
        
        with open(temp_file_path, "rb") as f:
            django_file = DjangoFile(f, name=file.filename)
            
            # Using sync_to_async for DB operations
            def create_doc():
                from documents.models import DocumentCollection
                collection = None
                if collection_id:
                    collection = DocumentCollection.objects.filter(id=collection_id, owner=user).first()
                    if not collection:
                        raise ValueError("Collection not found or permission denied.")
                
                DocumentService.validate_file(django_file)
                ext = os.path.splitext(django_file.name)[1].lower().replace('.', '')
                
                doc = Document(
                    uploaded_by=user,
                    collection=collection,
                    file_name=django_file.name,
                    file_type=ext,
                    file_path=django_file,
                    processing_status='UPLOADING'
                )
                doc.save()
                return doc
                
            doc = await sync_to_async(create_doc)()
            
            from documents.tasks import process_document_task
            task = process_document_task.delay(doc.id)
            
            doc.task_id = task.id
            await sync_to_async(doc.save)(update_fields=['task_id'])
            
            return DocumentDTO.model_validate(doc)
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str, user=Depends(get_current_user)):
    from celery.result import AsyncResult
    from config.celery import app as celery_app
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.state == 'FAILURE':
        response["error"] = str(task_result.result)
        
    return JSONResponse(content=response)

@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str, user=Depends(get_current_user)):
    from config.celery import app as celery_app
    
    # Send revoke signal
    celery_app.control.revoke(task_id, terminate=True)
    
    # We should also try to mark the document as FAILED/CANCELLED if we can find it
    async def mark_cancelled():
        try:
            doc = await Document.objects.aget(task_id=task_id, uploaded_by=user)
            if doc.processing_status not in ['COMPLETED', 'FAILED']:
                doc.processing_status = 'FAILED'
                await sync_to_async(doc.save)(update_fields=['processing_status'])
        except Document.DoesNotExist:
            pass
            
    await mark_cancelled()
    
    return JSONResponse(content={"task_id": task_id, "status": "CANCELLED"})
