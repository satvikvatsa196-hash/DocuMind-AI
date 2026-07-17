import json
import os
import logging
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # We can switch this to ChatGoogleGenerativeAI easily by changing this initialization
        api_key = os.environ.get("OPENAI_API_KEY", "dummy_key")
        self.llm = ChatOpenAI(temperature=0.0, openai_api_key=api_key, model_name="gpt-3.5-turbo")

    def generate_answer(self, question, context_chunks, chat_history=None):
        if chat_history is None:
            chat_history = []
            
        # Build context string
        context_text = ""
        for idx, chunk in enumerate(context_chunks):
            metadata = chunk.get("metadata", {})
            source = metadata.get("source", "Unknown Document")
            page = metadata.get("page_number", "-1")
            
            context_text += f"\n--- Context Chunk {idx+1} (Source: {source}, Page: {page}) ---\n"
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
      "page_number": "1"
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
            
            # Clean up potential markdown formatting from LLMs
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {response.content}")
            return {
                "answer": "I processed the answer but failed to format it correctly.",
                "citations": []
            }
        except Exception as e:
            logger.error(f"LLM API Call failed: {e}")
            return {
                "answer": "An error occurred while generating the answer.",
                "citations": []
            }
