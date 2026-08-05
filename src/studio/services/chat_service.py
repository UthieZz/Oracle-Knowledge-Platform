import os
from typing import List, Dict, Any
from src.studio.services.search_service import SearchService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ChatService:
    """Service for grounded chat with citations using the Gemini Developer API."""
    
    def __init__(self, search_service: SearchService):
        self.search_service = search_service
        
        # Configuration for Gemini API
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
        
        self._init_genai()

    def _init_genai(self):
        """Initializes Google Gen AI client (Developer API)."""
        try:
            from google import genai
            if not self.api_key:
                print("Warning: GEMINI_API_KEY not found in environment. Chat may fail.")
            
            self.genai_client = genai.Client(api_key=self.api_key)
            print(f"ChatService initialized with Gemini Developer API (Model: {self.model_name})")
        except ImportError:
            raise ImportError("google-genai is required for Gemini Developer API support. Install with 'pip install google-genai'.")

    def chat(self, query: str) -> Dict[str, Any]:
        """Performs grounded chat by retrieving context and generating a response."""
        print(f"DEBUG [Chat]: Input Query: {query}", flush=True)
        # 1. Retrieve context
        search_results = self.search_service.search(query)
        print(f"DEBUG [Search]: Found {len(search_results)} results.", flush=True)
        
        context_parts = []
        citations = []
        
        for idx, result in enumerate(search_results[:5]): # Use top 5 results as context
            print(f"DEBUG [Result {idx+1}]: Structure: {result}", flush=True)
            platform = result.get("source_platform") or result.get("provenance", {}).get("source_platform", "Unknown")
            conv_id = result.get("id")
            print(f"DEBUG [Result {idx+1}]: Platform: {platform}, ID: {conv_id}", flush=True)
            
            content = self.search_service.knowledge_service.get_conversation_details(
                platform, 
                conv_id
            )
            
            if content:
                print(f"DEBUG [Content {idx+1}]: Successfully retrieved content. Structure: {content}", flush=True)
                # Format context for the LLM
                messages_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in content.get("messages", [])])
                context_parts.append(f"SOURCE {idx+1} (Title: {result.get('title')}):\n{messages_text}")
                citations.append({
                    "id": conv_id,
                    "title": result.get("title"),
                    "platform": platform,
                    "source_index": idx + 1
                })
            else:
                print(f"DEBUG [Content {idx+1}]: FAILED to retrieve content for Platform: {platform}, ID: {conv_id}", flush=True)
        
        context_str = "\n\n---\n\n".join(context_parts)
        print(f"DEBUG [Context]: Assembled context length: {len(context_str)} characters.", flush=True)
        
        system_instruction = (
            "You are Oracle AI, a knowledge assistant for the Oracle Knowledge Platform. "
            "Your goal is to answer user queries using ONLY the provided context from their second brain. "
            "If the answer is not in the context, say you don't know based on the current knowledge. "
            "Always cite your sources using [SOURCE N] notation where N is the source index provided in the context."
        )
        
        prompt = f"Context:\n{context_str}\n\nUser Query: {query}\n\nAnswer:"
        print(f"DEBUG [Prompt]: Full Prompt: {prompt}", flush=True)
        
        try:
            # Gemini Developer API call
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.2
                }
            )
            answer = response.text
            print(f"DEBUG [Gemini]: Response: {answer}", flush=True)
            
            return {
                "answer": answer,
                "citations": citations,
                "query": query
            }
        except Exception as e:
            print(f"DEBUG [Gemini]: Error: {e}", flush=True)
            return {
                "answer": f"I encountered an error while processing your request: {str(e)}",
                "citations": [],
                "query": query
            }
