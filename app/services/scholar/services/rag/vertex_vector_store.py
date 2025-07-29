import logging
from typing import List, Dict, Any, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from google.cloud.aiplatform_v1 import MatchServiceClient
from google.cloud.aiplatform_v1.types import FindNeighborsRequest, IndexDatapoint
import numpy as np
from app.config.config import get_settings

logger = logging.getLogger(__name__)

class VertexVectorStore:
    """
    Vertex AI Vector Search implementation to replace Qdrant
    """

    def __init__(self):
        self.settings = get_settings()
        self.project_id = self.settings.vertex_project_id
        self.location = self.settings.vertex_location

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)

        # Vector Search configuration
        self.index_id = getattr(self.settings, 'vertex_index_id', None)
        self.endpoint_id = getattr(self.settings, 'vertex_endpoint_id', None)
        self.deployed_index_id = getattr(self.settings, 'vertex_deployed_index_id', None)

        # Initialize clients
        self.match_client = MatchServiceClient()

        # Cache for index and endpoint objects
        self._index = None
        self._endpoint = None

    @property
    def index(self) -> Optional[MatchingEngineIndex]:
        """Lazy load the index"""
        if self._index is None and self.index_id:
            try:
                self._index = aiplatform.MatchingEngineIndex(
                    index_name=f"projects/{self.project_id}/locations/{self.location}/indexes/{self.index_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to load index {self.index_id}: {e}")
        return self._index

    @property
    def endpoint(self) -> Optional[MatchingEngineIndexEndpoint]:
        """Lazy load the endpoint"""
        if self._endpoint is None and self.endpoint_id:
            try:
                self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
                    index_endpoint_name=f"projects/{self.project_id}/locations/{self.location}/indexEndpoints/{self.endpoint_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to load endpoint {self.endpoint_id}: {e}")
        return self._endpoint

    def get_vectors(self, doc_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all vectors for given document ID using similarity search

        Args:
            doc_id: Document identifier
            limit: Maximum number of vectors to return

        Returns:
            List of dictionaries with 'id' and 'vector' keys
        """
        try:
            if not self.endpoint or not self.deployed_index_id:
                logger.error("Vertex AI endpoint or deployed index not configured")
                return []

            # Create a dummy query vector (we'll filter by doc_id in metadata)
            # This is a workaround since Vertex AI doesn't support pure metadata filtering
            dummy_vector = [0.0] * 768  # Assuming 768-dimensional vectors

            # Perform similarity search
            response = self._find_neighbors(
                query_vector=dummy_vector,
                num_neighbors=limit,
                filter_doc_id=doc_id
            )

            results = []
            for neighbor in response.nearest_neighbors:
                for match in neighbor.neighbors:
                    # Extract vector from datapoint if available
                    vector = list(match.datapoint.feature_vector) if match.datapoint.feature_vector else []
                    results.append({
                        "id": match.datapoint.datapoint_id,
                        "vector": vector
                    })

            return results

        except Exception as e:
            logger.error(f"Error fetching vectors for doc_id {doc_id}: {e}")
            return []

    def search_vectors(self, query_vector: List[float], limit: int = 10,
                      doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors

        Args:
            query_vector: Query vector for similarity search
            limit: Maximum number of results to return
            doc_id: Optional document ID filter

        Returns:
            List of dictionaries with 'id', 'vector', and 'score' keys
        """
        try:
            if not self.endpoint or not self.deployed_index_id:
                logger.error("Vertex AI endpoint or deployed index not configured")
                return []

            response = self._find_neighbors(
                query_vector=query_vector,
                num_neighbors=limit,
                filter_doc_id=doc_id
            )

            results = []
            for neighbor in response.nearest_neighbors:
                for match in neighbor.neighbors:
                    vector = list(match.datapoint.feature_vector) if match.datapoint.feature_vector else []
                    results.append({
                        "id": match.datapoint.datapoint_id,
                        "vector": vector,
                        "score": match.distance
                    })

            return results

        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            return []

    def _find_neighbors(self, query_vector: List[float], num_neighbors: int = 10,
                       filter_doc_id: Optional[str] = None) -> Any:
        """
        Internal method to find neighbors using Vertex AI Vector Search
        """
        endpoint_name = f"projects/{self.project_id}/locations/{self.location}/indexEndpoints/{self.endpoint_id}"

        # Create the query datapoint
        query_datapoint = IndexDatapoint(
            feature_vector=query_vector
        )

        # Create the query
        query = FindNeighborsRequest.Query(
            datapoint=query_datapoint,
            neighbor_count=num_neighbors
        )

        # Add filtering if doc_id is provided
        if filter_doc_id:
            # Note: This requires the index to be configured with metadata filtering
            query.restricts = [
                FindNeighborsRequest.Query.Restrict(
                    namespace="doc_id",
                    allow_list=[filter_doc_id]
                )
            ]

        # Create the request
        request = FindNeighborsRequest(
            index_endpoint=endpoint_name,
            deployed_index_id=self.deployed_index_id,
            queries=[query]
        )

        # Execute the search
        response = self.match_client.find_neighbors(request=request)
        return response

    def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """
        Insert or update vectors in the index

        Args:
            vectors: List of dictionaries with 'id', 'vector', and optional 'metadata'

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.index:
                logger.error("Vertex AI index not configured")
                return False

            # Convert to IndexDatapoint format
            datapoints = []
            for vector_data in vectors:
                datapoint = IndexDatapoint(
                    datapoint_id=vector_data["id"],
                    feature_vector=vector_data["vector"]
                )

                # Add metadata if provided
                if "metadata" in vector_data:
                    # Convert metadata to restricts format
                    restricts = []
                    for key, value in vector_data["metadata"].items():
                        restricts.append(f"{key}:{value}")
                    datapoint.restricts = restricts

                datapoints.append(datapoint)

            # Upsert datapoints
            operation = self.index.upsert_datapoints(datapoints=datapoints)

            # Wait for operation to complete
            operation.wait()

            logger.info(f"Successfully upserted {len(vectors)} vectors")
            return True

        except Exception as e:
            logger.error(f"Error upserting vectors: {e}")
            return False

    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """
        Delete vectors from the index

        Args:
            vector_ids: List of vector IDs to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.index:
                logger.error("Vertex AI index not configured")
                return False

            # Remove datapoints
            operation = self.index.remove_datapoints(datapoint_ids=vector_ids)

            # Wait for operation to complete
            operation.wait()

            logger.info(f"Successfully deleted {len(vector_ids)} vectors")
            return True

        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return False

    def create_index(self, display_name: str, dimensions: int = 768,
                    distance_measure: str = "COSINE_DISTANCE") -> Optional[str]:
        """
        Create a new Vertex AI Vector Search index

        Args:
            display_name: Display name for the index
            dimensions: Vector dimensions
            distance_measure: Distance measure (COSINE_DISTANCE, DOT_PRODUCT_DISTANCE, etc.)

        Returns:
            Index ID if successful, None otherwise
        """
        try:
            # Create index configuration
            index_config = {
                "dimensions": dimensions,
                "distance_measure_type": distance_measure,
                "algorithm_config": {
                    "tree_ah_config": {
                        "leaf_node_embedding_count": 500,
                        "leaf_nodes_to_search_percent": 7
                    }
                }
            }

            # Create the index
            index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=display_name,
                contents_delta_uri="gs://your-bucket/empty",  # Placeholder
                dimensions=dimensions,
                distance_measure_type=distance_measure
            )

            logger.info(f"Created index: {index.resource_name}")
            return index.name.split("/")[-1]  # Extract index ID

        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return None

    def deploy_index(self, index_id: str, endpoint_id: str,
                    deployed_index_id: str) -> bool:
        """
        Deploy an index to an endpoint

        Args:
            index_id: ID of the index to deploy
            endpoint_id: ID of the endpoint
            deployed_index_id: ID for the deployed index

        Returns:
            True if successful, False otherwise
        """
        try:
            endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=f"projects/{self.project_id}/locations/{self.location}/indexEndpoints/{endpoint_id}"
            )

            index = aiplatform.MatchingEngineIndex(
                index_name=f"projects/{self.project_id}/locations/{self.location}/indexes/{index_id}"
            )

            # Deploy the index
            operation = endpoint.deploy_index(
                index=index,
                deployed_index_id=deployed_index_id
            )

            # Wait for deployment to complete
            operation.wait()

            logger.info(f"Successfully deployed index {index_id} to endpoint {endpoint_id}")
            return True

        except Exception as e:
            logger.error(f"Error deploying index: {e}")
            return False
