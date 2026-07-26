import json
import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # We can switch this to ChatGoogleGenerativeAI easily by changing this initialization
        api_key = os.environ.get("OPENAI_API_KEY", "dummy_key")
        self.llm = ChatOpenAI(temperature=0.0, openai_api_key=api_key, model_name="gpt-3.5-turbo")

    def generate_answer(self, question, context_chunks, chat_history=None, is_debug=False):
        if chat_history is None:
            chat_history = []
            
        # Build context string
        context_text = ""
        chunk_map = {}
        for idx, chunk in enumerate(context_chunks):
            source = chunk.get("document_name", "Unknown Document")
            page = chunk.get("page_number", -1)
            chunk_id = chunk.get("chunk_id", -1)
            
            chunk_map[str(chunk_id)] = chunk
            
            context_text += f"\n--- Context Chunk {idx+1} (Source: {source}, Page: {page}, Chunk ID: {chunk_id}) ---\n"
            context_text += chunk.get("text", "")
            
        system_prompt = """You are a helpful AI document assistant. 
Answer the user's question ONLY using the provided document context. 
If the information is unavailable in the context, strictly say exactly: "I don't have enough information from the documents."

You MUST return your answer in valid JSON format matching this schema exactly:
{
  "answer": "Your detailed answer here.",
  "citations": [
    {
      "document_name": "filename.pdf",
      "page_number": "1",
      "chunk_id": "123"
    }
  ]
}

Only include citations for documents that actually helped you formulate the answer.
If you say you don't have enough information, the citations array should be empty.
Ensure your response is valid JSON. Do not include markdown code block formatting like ```json in the output, just raw JSON.
"""

        messages = [
            SystemMessage(content=system_prompt)
        ]
        
        # Append previous chat history
        for msg in chat_history:
            if msg["role"] == "USER":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "AI":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=f"Context:\n{context_text}\n\nQuestion: {question}"))

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            debug_info = None
            if is_debug:
                prompt_sent = ""
                for msg in messages:
                    prompt_sent += f"{msg.type.upper()}:\n{msg.content}\n\n"
                
                input_tokens = 0
                output_tokens = 0
                total_tokens = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    input_tokens = response.usage_metadata.get('input_tokens', 0)
                    output_tokens = response.usage_metadata.get('output_tokens', 0)
                    total_tokens = response.usage_metadata.get('total_tokens', 0)
                else:
                    # simple fallback estimation
                    input_tokens = len(prompt_sent) // 4
                    output_tokens = len(content) // 4
                    total_tokens = input_tokens + output_tokens
                
                debug_info = {
                    "prompt_sent": prompt_sent,
                    "token_count": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens
                    }
                }
            
            # Clean up potential markdown formatting from LLMs
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            parsed_response = json.loads(content.strip())
            
            # Deduplicate citations and add highlighted passages
            unique_citations = []
            seen_chunk_ids = set()
            retrieved_passages = []
            
            for cit in parsed_response.get("citations", []):
                c_id = str(cit.get("chunk_id"))
                if c_id not in seen_chunk_ids and c_id in chunk_map:
                    seen_chunk_ids.add(c_id)
                    unique_citations.append(cit)
                    orig_chunk = chunk_map[c_id]
                    retrieved_passages.append({
                        "document_name": orig_chunk.get("document_name"),
                        "page_number": orig_chunk.get("page_number"),
                        "chunk_id": orig_chunk.get("chunk_id"),
                        "chunk_text": orig_chunk.get("text"),
                        "relevance_score": orig_chunk.get("relevance_score")
                    })
                    
            # Sort retrieved passages by relevance score descending
            retrieved_passages.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            result = {
                "answer": parsed_response.get("answer", ""),
                "citations": unique_citations,
                "retrieved_passages": retrieved_passages
            }
            if debug_info:
                result["debug_info"] = debug_info
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {response.content}")
            return {
                "answer": "I processed the answer but failed to format it correctly.",
                "citations": [],
                "retrieved_passages": []
            }
        except Exception as e:
            logger.error(f"LLM API Call failed: {e}")
            return {
                "answer": "An error occurred while generating the answer.",
                "citations": [],
                "retrieved_passages": []
            }

    async def stream_generate_answer(self, question, context_chunks, chat_history=None, is_debug=False):
        if chat_history is None:
            chat_history = []
            
        context_text = ""
        citations = []
        for idx, chunk in enumerate(context_chunks):
            source = chunk.get("document_name", "Unknown Document")
            page = chunk.get("page_number", -1)
            chunk_id = chunk.get("chunk_id", -1)
            
            citations.append({
                "document_name": source,
                "page_number": page,
                "chunk_id": chunk_id,
                "chunk_text": chunk.get("text"),
                "relevance_score": chunk.get("relevance_score")
            })
            
            context_text += f"\n--- Context Chunk {idx+1} (Source: {source}, Page: {page}, Chunk ID: {chunk_id}) ---\n"
            context_text += chunk.get("text", "")
            
        system_prompt = """You are a helpful AI document assistant. 
Answer the user's question ONLY using the provided document context. 
If the information is unavailable in the context, strictly say exactly: "I don't have enough information from the documents."

Provide your answer as plain text without any markdown or JSON formatting.
"""

        messages = [
            SystemMessage(content=system_prompt)
        ]
        
        for msg in chat_history:
            if msg["role"] == "USER":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "AI":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=f"Context:\n{context_text}\n\nQuestion: {question}"))

        try:
            prompt_sent = ""
            if is_debug:
                for msg in messages:
                    prompt_sent += f"{msg.type.upper()}:\n{msg.content}\n\n"
                    
            input_tokens = 0
            output_tokens = 0
            
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    if is_debug:
                        output_tokens += len(chunk.content) // 4
                    yield {"token": chunk.content}
                    
            if is_debug:
                input_tokens = len(prompt_sent) // 4
                yield {"debug_info": {
                    "prompt_sent": prompt_sent,
                    "token_count": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    }
                }}
                    
            # After finishing the text, yield the citations
            yield {"citations": citations}
        except Exception as e:
            logger.error(f"Error in LLM stream: {e}")
            yield {"token": f"\n\n[Error: {str(e)}]"}

