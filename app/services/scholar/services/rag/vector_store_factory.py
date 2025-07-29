import logging
from app.config.config import get_settings
from .vertex_vector_store import VertexVectorStore

logger = logging.getLogger(__name__)

class VectorStoreFactory:
    """
    Factory class to create Vertex AI Vector Search instances
    Note: Qdrant support has been deprecated in favor of Vertex AI Vector Search
    """

    @staticmethod
    def create_vector_store() -> VertexVectorStore:
        """
        Create a Vertex AI Vector Search instance

        Returns:
            VertexVectorStore instance
        """
        logger.info("Using Vertex AI Vector Search backend")
        return VertexVectorStore()

    @staticmethod
    def get_available_backends():
        """
        Get list of available vector store backends

        Returns:
            List of available backend names
        """
        return ["vertex"]
