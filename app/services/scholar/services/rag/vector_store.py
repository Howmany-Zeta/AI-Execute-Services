from qdrant_client import QdrantClient
from app.config.config import get_settings

class VectorStore:
    def __init__(self):
        settings = get_settings()
        # Connect to Qdrant; replace with actual host/port or environment config
        self.client = QdrantClient(url=settings.qdrant_url or "http://qdrant:6333")
        self.collection = settings.qdrant_collection or "documents"

    def get_vectors(self, doc_id: str):
        # Fetch all vectors for given document ID
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=[0]*768,  # placeholder; Qdrant requires a vector but filter isolates results
            filter={
                "must": [
                    {"key": "doc_id", "match": {"value": doc_id}}
                ]
            },
            limit=100
        )
        return [{"id": str(h.id), "vector": h.vector} for h in hits]
