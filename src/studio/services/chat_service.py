import os
from typing import List, Dict, Any, Optional
from src.studio.services.search_service import SearchService
from dotenv import load_dotenv

load_dotenv()

INSUFFICIENT_EVIDENCE = (
    "I do not have sufficient evidence in the compiled knowledge to answer this question."
)


class ChatService:
    """Grounded chat over compiled knowledge objects (Stage 3).

    Contract:
      Question → retrieve ranked knowledge (KO first) → top 6 bound context
      → cite [Source N] with stable ids + source_platform → decline when empty.
    """

    def __init__(self, search_service: SearchService):
        self.search_service = search_service
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
        self.genai_client = None
        self._init_genai()

    def _init_genai(self):
        try:
            from google import genai

            if not self.api_key:
                print("Warning: GEMINI_API_KEY not found in environment. Chat may fail.")
            self.genai_client = genai.Client(api_key=self.api_key)
            print(
                f"ChatService initialized with Gemini Developer API (Model: {self.model_name})"
            )
        except ImportError:
            # Allow unit tests without google-genai installed.
            print(
                "Warning: google-genai not installed. Live chat will fail; retrieval tests still run."
            )
            self.genai_client = None

    def _build_context(self, search_results: List[Dict[str, Any]], limit: int = 6):
        context_parts: List[str] = []
        citations: List[Dict[str, Any]] = []

        for idx, result in enumerate(search_results[:limit]):
            platform = (
                result.get("source_platform")
                or result.get("platform")
                or "Unknown"
            )
            result_id = result.get("id") or f"result-{idx+1}"
            title = result.get("title") or result_id
            body = result.get("content") or ""

            # Fallback only if search did not already attach body and type is conversation
            if not body and result.get("type") == "conversation":
                details = self.search_service.knowledge_service.get_conversation_details(
                    platform, result_id
                )
                if details and isinstance(details.get("messages"), list):
                    body = "\n".join(
                        f"{m.get('role')}: {m.get('content')}"
                        for m in details["messages"]
                        if m.get("content")
                    )

            if not body:
                continue

            bounded = body if len(body) <= 1500 else f"{body[:1500]}... [truncated]"
            source_num = idx + 1
            context_parts.append(
                f'[Source {source_num}: "{title}" ({platform}) - ID: {result_id}]\n{bounded}'
            )
            citations.append(
                {
                    "id": result_id,
                    "title": title,
                    "platform": platform,
                    "source_index": source_num,
                    "snippet": body[:180] + ("..." if len(body) > 180 else ""),
                    "type": result.get("type") or "knowledge",
                }
            )

        return context_parts, citations

    def chat(self, query: str) -> Dict[str, Any]:
        """Grounded ask. Declines when no compiled evidence is available."""
        trimmed = (query or "").strip()
        if not trimmed:
            return {
                "answer": "Please enter a question about your compiled knowledge.",
                "citations": [],
                "query": query or "",
            }

        search_results = self.search_service.search(trimmed) or []
        # Prefer knowledge type ordering already applied by search; keep top slice
        context_parts, citations = self._build_context(search_results, limit=6)

        if not context_parts:
            return {
                "answer": INSUFFICIENT_EVIDENCE,
                "citations": [],
                "query": trimmed,
            }

        context_str = "\n\n---\n\n".join(context_parts)

        system_instruction = (
            "You are Oracle AI, the evidence-grounded reasoning layer of the "
            "Oracle Knowledge Platform (OKP). Answer using ONLY the provided "
            "EVIDENCE SOURCES from compiled knowledge. If the evidence does not "
            "contain sufficient facts, state exactly: "
            f'"{INSUFFICIENT_EVIDENCE}" '
            "Cite sources with [Source N] matching the source numbers in context. "
            "Do not fabricate, extrapolate, or invent facts."
        )

        prompt = (
            f"EVIDENCE SOURCES FROM COMPILED KNOWLEDGE:\n{context_str}\n\n"
            f"USER QUESTION:\n{trimmed}\n\nAnswer:"
        )

        if self.genai_client is None:
            return {
                "answer": (
                    "Gemini client is not configured (missing API key or google-genai). "
                    "Retrieval succeeded; install/configure Gemini to generate answers."
                ),
                "citations": citations,
                "query": trimmed,
                "hasError": True,
            }

        try:
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.1,
                },
            )
            answer = getattr(response, "text", None) or INSUFFICIENT_EVIDENCE
            return {
                "answer": answer,
                "citations": citations,
                "query": trimmed,
            }
        except Exception as e:
            return {
                "answer": f"I encountered an error while processing your request: {str(e)}",
                "citations": [],
                "query": trimmed,
                "hasError": True,
            }
