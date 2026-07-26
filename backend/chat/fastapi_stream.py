import json
import asyncio
import jwt
import logging
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from django.conf import settings
from asgiref.sync import sync_to_async

from django.contrib.auth import get_user_model
from chat.models import ChatSession, ChatMessage
from documents.models import Document, DocumentCollection
from ai_engine.retriever import RetrieverService
from ai_engine.llm import LLMService

logger = logging.getLogger(__name__)

app = FastAPI(title="DocuMind AI Streaming API")

class StreamRequest(BaseModel):
    query: str
    session_id: Optional[int] = None
    collection_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    debug: Optional[bool] = False

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        User = get_user_model()
        user = await sync_to_async(User.objects.get)(id=user_id)
        return user
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/stream/")
async def stream_chat(request: StreamRequest, user=Depends(get_current_user)):
    import time
    
    query = request.query
    session_id = request.session_id
    collection_id = request.collection_id
    document_ids = request.document_ids
    debug = request.debug
    
    is_debug = debug and getattr(settings, 'ENABLE_DEBUG_MODE', True)
    total_start = time.time()

    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")

    # We need to run DB queries in sync context
    async def get_session_and_history():
        session = None
        chat_history = []
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
                if session.collection:
                    nonlocal collection_id
                    collection_id = session.collection.id
                
                recent_messages = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:10]
                for msg in reversed(list(recent_messages)):
                    chat_history.append({
                        "role": msg.role,
                        "content": msg.message
                    })
                
                # Save user message
                ChatMessage.objects.create(session=session, role='USER', message=query)
            except ChatSession.DoesNotExist:
                raise HTTPException(status_code=404, detail="Session not found.")
        return session, chat_history

    session, chat_history = await sync_to_async(get_session_and_history)()

    # Get allowed documents
    async def get_allowed_documents():
        allowed_docs = Document.objects.filter(uploaded_by=user)
        if collection_id:
            try:
                collection = DocumentCollection.objects.get(id=collection_id, owner=user)
                allowed_docs = allowed_docs.filter(collection=collection)
            except DocumentCollection.DoesNotExist:
                pass
        if document_ids:
            allowed_docs = allowed_docs.filter(id__in=document_ids)
            
        return list(allowed_docs.values_list('id', flat=True))

    user_document_ids = await sync_to_async(get_allowed_documents)()

    if not user_document_ids:
        async def no_docs_response():
            yield "data: " + json.dumps({"token": "You have no documents available to search in this context."}) + "\n\n"
            if session:
                await sync_to_async(ChatMessage.objects.create)(session=session, role='AI', message="You have no documents available to search in this context.")
            yield "event: end\ndata: {}\n\n"
        return StreamingResponse(no_docs_response(), media_type="text/event-stream")

    # Retrieve context
    retrieval_start = time.time()
    embedding_dim = 0
    if is_debug:
        context_chunks, embedding_dim = await sync_to_async(RetrieverService.retrieve_context)(
            query, document_ids=user_document_ids, top_k=5, is_debug=True
        )
    else:
        context_chunks = await sync_to_async(RetrieverService.retrieve_context)(
            query, document_ids=user_document_ids, top_k=5
        )
    retrieval_latency = time.time() - retrieval_start

    llm_service = LLMService()

    async def generate():
        full_answer = ""
        llm_start = time.time()
        try:
            async for chunk_data in llm_service.stream_generate_answer(query, context_chunks, chat_history, is_debug=is_debug):
                if chunk_data.get("token"):
                    full_answer += chunk_data["token"]
                    yield "data: " + json.dumps({"token": chunk_data["token"]}) + "\n\n"
                elif chunk_data.get("citations"):
                    yield "data: " + json.dumps({"citations": chunk_data["citations"]}) + "\n\n"
                elif chunk_data.get("debug_info"):
                    llm_latency = time.time() - llm_start
                    total_latency = time.time() - total_start
                    debug_info = chunk_data["debug_info"]
                    debug_data = {
                        "original_user_question": query,
                        "generated_embedding_dimension": embedding_dim,
                        "retrieval_query": query,
                        "retrieved_chunks": [c.get("text") for c in context_chunks],
                        "similarity_scores": [c.get("relevance_score") for c in context_chunks],
                        "chunk_ids": [c.get("chunk_id") for c in context_chunks],
                        "document_names": [c.get("document_name") for c in context_chunks],
                        "prompt_sent": debug_info.get("prompt_sent", ""),
                        "token_count": debug_info.get("token_count", {}),
                        "response_generation_time": f"{llm_latency:.4f}s",
                        "retrieval_latency": f"{retrieval_latency:.4f}s",
                        "total_latency": f"{total_latency:.4f}s"
                    }
                    yield "data: " + json.dumps({"debug": debug_data}) + "\n\n"
                    
                    logger.info(f"DEBUG MODE - Query: {query}, Latency: {total_latency:.4f}s, Stream: True")
            
            # After streaming is complete, save the full response
            if session:
                await sync_to_async(ChatMessage.objects.create)(session=session, role='AI', message=full_answer)
                
            yield "event: end\ndata: {}\n\n"
            
        except asyncio.CancelledError:
            # Handle client disconnect gracefully
            logger.info("Client disconnected during stream")
            if session and full_answer:
                await sync_to_async(ChatMessage.objects.create)(session=session, role='AI', message=full_answer)
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield "event: error\ndata: " + json.dumps({"detail": "An error occurred during generation."}) + "\n\n"
            if session and full_answer:
                await sync_to_async(ChatMessage.objects.create)(session=session, role='AI', message=full_answer)

    return StreamingResponse(generate(), media_type="text/event-stream")
