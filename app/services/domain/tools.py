from app.tools import get_tool
from app.core.registry import get_ai_service

class DomainTools:
    """
    Encapsulates tool usage rules for Domain mode.
    """
    def __init__(self):
        self.db = get_tool("db_api")
        # Use the domain RAG service instead of the RAG tool
        self.rag_service = get_ai_service("domain", "rag")

    def query(self, text: str) -> str:
        """
        Perform domain-specific DB query; if no data, fallback to RAG.
        """
        result = self.db.run(text)
        if not result or "no result" in result.lower():
            # Adapt to use the RAG service
            rag_result = self.rag_service.run({"query": text}, {})
            result = rag_result.get("result", f"[RAG retrieved]: context for '{text}'")
        return result
