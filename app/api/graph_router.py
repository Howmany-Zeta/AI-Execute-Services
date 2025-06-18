from fastapi import APIRouter, HTTPException
from app.core.registry import get_ai_service

router = APIRouter()

@router.get("/{doc_id}")
async def get_graph(doc_id: str, threshold: float = 0.5):
    """
    返回指定文档的知识图谱结构数据
    """
    try:
        # Use the domain RAG service instead of directly accessing the RAG modules
        rag_service = get_service("domain", "rag")
        result = rag_service.run({"doc_id": doc_id, "threshold": threshold}, {})
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result.get("graph", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
