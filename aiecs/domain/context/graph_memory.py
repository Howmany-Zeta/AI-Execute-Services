"""
Graph Memory Integration for ContextEngine

Extends ContextEngine with knowledge graph memory capabilities,
allowing agents to store and retrieve knowledge from the graph
during conversations.
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime

from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

if TYPE_CHECKING:
    from aiecs.infrastructure.graph_storage.protocols import GraphMemoryMixinProtocol

logger = logging.getLogger(__name__)


class GraphMemoryMixin:
    """
    Mixin to add graph memory capabilities to ContextEngine.

    This mixin extends ContextEngine with methods to:
    - Store knowledge entities and relations
    - Retrieve knowledge based on context
    - Link conversation to knowledge graph
    - Maintain graph-based conversation context

    This mixin expects the class it's mixed into to implement `GraphMemoryMixinProtocol`,
    specifically the `graph_store` attribute.

    Usage:
        class ContextEngineWithGraph(ContextEngine, GraphMemoryMixin):
            def __init__(self, graph_store: GraphStore, ...):
                super().__init__(...)
                self.graph_store = graph_store
    """

    if TYPE_CHECKING:
        # Type hint for mypy: this mixin expects GraphMemoryMixinProtocol
        graph_store: Optional[GraphStore]

    async def store_knowledge(
        self,
        session_id: str,
        entity: Entity,
        relations: Optional[List[Relation]] = None,
        link_to_session: bool = True,
    ) -> bool:
        """
        Store knowledge entity (and optional relations) to the graph.

        Args:
            session_id: Session identifier
            entity: Entity to store
            relations: Optional list of relations involving this entity
            link_to_session: Whether to create a relation linking entity to session

        Returns:
            True if stored successfully, False otherwise

        Example:
            # Store a new person entity from conversation
            person = Entity(
                id="person_123",
                entity_type="Person",
                properties={"name": "Alice", "role": "Engineer"}
            )

            await context_engine.store_knowledge(
                session_id="session_1",
                entity=person,
                link_to_session=True
            )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available, cannot store knowledge")
            return False

        try:
            # Store entity
            await self.graph_store.add_entity(entity)
            logger.debug(f"Stored entity {entity.id} to graph")

            # Store relations if provided
            if relations:
                for relation in relations:
                    await self.graph_store.add_relation(relation)
                logger.debug(f"Stored {len(relations)} relations to graph")

            # Link entity to session if requested
            if link_to_session:
                session_entity_id = f"session_{session_id}"

                # Create session entity if it doesn't exist
                session_entity = await self.graph_store.get_entity(session_entity_id)
                if not session_entity:
                    session_entity = Entity(
                        id=session_entity_id,
                        entity_type="Session",
                        properties={
                            "session_id": session_id,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.graph_store.add_entity(session_entity)

                # Create MENTIONED_IN relation
                relation = Relation(
                    id=f"mention_{entity.id}_{session_id}_{datetime.utcnow().timestamp()}",
                    source_id=entity.id,
                    target_id=session_entity_id,
                    relation_type="MENTIONED_IN",
                    properties={"timestamp": datetime.utcnow().isoformat()},
                )
                await self.graph_store.add_relation(relation)
                logger.debug(f"Linked entity {entity.id} to session {session_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to store knowledge: {e}")
            return False

    async def retrieve_knowledge(
        self,
        session_id: str,
        query: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        include_session_context: bool = True,
    ) -> List[Entity]:
        """
        Retrieve knowledge entities relevant to the session and/or query.

        Args:
            session_id: Session identifier
            query: Optional search query (uses embedding if available)
            entity_types: Optional filter by entity types
            limit: Maximum number of entities to retrieve
            include_session_context: Whether to include entities mentioned in this session

        Returns:
            List of relevant entities

        Example:
            # Retrieve people mentioned in this session
            people = await context_engine.retrieve_knowledge(
                session_id="session_1",
                entity_types=["Person"],
                limit=5
            )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available, cannot retrieve knowledge")
            return []

        try:
            entities = []
            seen = set()

            # 1. Get session-specific entities if requested
            if include_session_context:
                session_entities = await self._get_session_entities(session_id)
                for entity in session_entities:
                    if entity.id not in seen:
                        seen.add(entity.id)
                        entities.append(entity)

            # 2. If query provided, use embedding-based search (if available)
            if query and len(entities) < limit:
                remaining_limit = limit - len(entities)
                
                # Try embedding-based search first
                query_embedding = await self._generate_query_embedding(query)
                
                if query_embedding:
                    # Use vector search with embedding
                    try:
                        # Handle entity_types: vector_search takes single entity_type
                        # If multiple types specified, search each separately and combine
                        vector_results = []
                        
                        if entity_types:
                            # Search each entity type separately
                            for entity_type in entity_types:
                                type_results = await self.graph_store.vector_search(
                                    query_embedding=query_embedding,
                                    entity_type=entity_type,
                                    max_results=remaining_limit,
                                    score_threshold=0.0,
                                )
                                vector_results.extend(type_results)
                        else:
                            # No entity type filter - search all
                            vector_results = await self.graph_store.vector_search(
                                query_embedding=query_embedding,
                                entity_type=None,
                                max_results=remaining_limit,
                                score_threshold=0.0,
                            )
                        
                        # Extract entities from (entity, score) tuples
                        for entity, score in vector_results:
                            if entity.id not in seen:
                                seen.add(entity.id)
                                entities.append(entity)
                                if len(entities) >= limit:
                                    break
                                    
                        logger.debug(f"Retrieved {len(vector_results)} entities via vector search")
                        
                    except Exception as e:
                        logger.warning(f"Vector search failed: {e}, falling back to text search")
                        # Fallback to text search below
                        query_embedding = None
                
                # Fallback to text search if embeddings unavailable or vector search failed
                if not query_embedding and len(entities) < limit:
                    remaining_limit = limit - len(entities)
                    try:
                        # Handle entity_types: text_search takes single entity_type
                        text_results = []
                        
                        if entity_types:
                            # Search each entity type separately
                            for entity_type in entity_types:
                                type_results = await self.graph_store.text_search(
                                    query_text=query,
                                    entity_type=entity_type,
                                    max_results=remaining_limit,
                                    score_threshold=0.0,
                                )
                                text_results.extend(type_results)
                        else:
                            # No entity type filter - search all
                            text_results = await self.graph_store.text_search(
                                query_text=query,
                                entity_type=None,
                                max_results=remaining_limit,
                                score_threshold=0.0,
                            )
                        
                        # Extract entities from (entity, score) tuples
                        for entity, score in text_results:
                            if entity.id not in seen:
                                seen.add(entity.id)
                                entities.append(entity)
                                if len(entities) >= limit:
                                    break
                                    
                        logger.debug(f"Retrieved {len(text_results)} entities via text search")
                        
                    except Exception as e:
                        logger.warning(f"Text search also failed: {e}")

            # 3. Filter by entity types if specified (for session entities that weren't filtered)
            if entity_types:
                entities = [e for e in entities if e.entity_type in entity_types]

            return entities[:limit]

        except Exception as e:
            logger.error(f"Failed to retrieve knowledge: {e}")
            return []

    async def _generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for query text using available embedding service.
        
        Checks if the class has an llm_client attribute that supports get_embeddings.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector or None if unavailable
        """
        try:
            # Check if class has llm_client attribute
            if not hasattr(self, "llm_client") or self.llm_client is None:
                logger.debug("No llm_client available for embedding generation")
                return None
            
            # Check if llm_client supports get_embeddings
            if not hasattr(self.llm_client, "get_embeddings"):
                logger.debug(f"LLM client ({type(self.llm_client).__name__}) does not support embeddings")
                return None
            
            # Verify the method is callable
            get_embeddings_method = getattr(self.llm_client, "get_embeddings", None)
            if not callable(get_embeddings_method):
                logger.debug(f"LLM client has 'get_embeddings' attribute but it's not callable")
                return None
            
            # Generate embedding
            embeddings = await self.llm_client.get_embeddings(
                texts=[query],
                model=None,  # Use default embedding model
            )
            
            if embeddings and len(embeddings) > 0 and embeddings[0]:
                logger.debug(f"Generated query embedding (dimension: {len(embeddings[0])})")
                return embeddings[0]
            
            return None
            
        except NotImplementedError:
            logger.debug("Embedding generation not implemented for this LLM client")
            return None
        except Exception as e:
            logger.warning(f"Failed to generate query embedding: {e}")
            return None

    async def _get_session_entities(self, session_id: str) -> List[Entity]:
        """Get all entities mentioned in this session."""
        if self.graph_store is None:
            return []
        try:
            session_entity_id = f"session_{session_id}"

            # Get session entity
            session_entity = await self.graph_store.get_entity(session_entity_id)
            if not session_entity:
                return []

            # Get all entities with MENTIONED_IN relation to this session
            # Note: We need to traverse backwards from session to entities
            # get_neighbors only accepts single relation_type, not a list
            # neighbors = await self.graph_store.get_neighbors(
            #     session_entity_id,
            #     relation_type="MENTIONED_IN",
            #     direction="incoming"  # Get entities that point TO the session
            # )  # Reserved for future use

            # Neighbors are entities that have MENTIONED_IN relation to session
            # We need to get entities that point TO the session
            # This requires iterating through all entities (not ideal, but
            # functional)

            # For now, return empty - proper implementation would require
            # inverse index or traversal from session
            # This is a simplified implementation
            return []

        except Exception as e:
            logger.error(f"Failed to get session entities: {e}")
            return []

    async def add_graph_conversation_context(
        self,
        session_id: str,
        entity_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add graph-based context to conversation.

        Links specific entities to the current conversation session,
        providing additional context for the agent.

        Args:
            session_id: Session identifier
            entity_ids: List of entity IDs to link to session
            metadata: Optional metadata about the context

        Returns:
            True if successful, False otherwise

        Example:
            # Add context entities to conversation
            await context_engine.add_graph_conversation_context(
                session_id="session_1",
                entity_ids=["person_alice", "company_techcorp"],
                metadata={"context_type": "background_knowledge"}
            )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available, cannot add graph context")
            return False

        try:
            session_entity_id = f"session_{session_id}"

            # Ensure session entity exists
            session_entity = await self.graph_store.get_entity(session_entity_id)
            if not session_entity:
                session_entity = Entity(
                    id=session_entity_id,
                    entity_type="Session",
                    properties={
                        "session_id": session_id,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
                await self.graph_store.add_entity(session_entity)

            # Link each entity to session
            for entity_id in entity_ids:
                # Verify entity exists
                entity = await self.graph_store.get_entity(entity_id)
                if not entity:
                    logger.warning(f"Entity {entity_id} not found, skipping")
                    continue

                # Create CONTEXT_FOR relation
                relation = Relation(
                    id=f"context_{entity_id}_{session_id}_{datetime.utcnow().timestamp()}",
                    source_id=entity_id,
                    target_id=session_entity_id,
                    relation_type="CONTEXT_FOR",
                    properties={
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": metadata or {},
                    },
                )
                await self.graph_store.add_relation(relation)

            logger.info(f"Added {len(entity_ids)} entities as context for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add graph conversation context: {e}")
            return False

    async def get_session_knowledge_graph(self, session_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Get a subgraph of knowledge relevant to this session.

        Returns entities and relations mentioned or used as context
        in this session, up to a specified depth.

        Args:
            session_id: Session identifier
            max_depth: Maximum depth for graph traversal

        Returns:
            Dictionary with 'entities' and 'relations' lists

        Example:
            # Get knowledge graph for session
            subgraph = await context_engine.get_session_knowledge_graph(
                session_id="session_1",
                max_depth=2
            )
            print(f"Entities: {len(subgraph['entities'])}")
            print(f"Relations: {len(subgraph['relations'])}")
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return {"entities": [], "relations": []}

        try:
            session_entity_id = f"session_{session_id}"

            # Get session entity
            session_entity = await self.graph_store.get_entity(session_entity_id)
            if not session_entity:
                return {"entities": [], "relations": []}

            entities = [session_entity]
            relations: List[Any] = []
            visited = {session_entity_id}

            # Traverse from session entity
            current_level = [session_entity_id]

            for depth in range(max_depth):
                next_level = []

                for entity_id in current_level:
                    # Get neighbors (check both relation types separately)
                    neighbors_mentioned = await self.graph_store.get_neighbors(
                        entity_id,
                        relation_type="MENTIONED_IN",
                        direction="both",
                    )
                    neighbors_context = await self.graph_store.get_neighbors(
                        entity_id,
                        relation_type="CONTEXT_FOR",
                        direction="both",
                    )
                    # Combine and deduplicate
                    neighbors = list({n.id: n for n in neighbors_mentioned + neighbors_context}.values())

                    for neighbor in neighbors:
                        if neighbor.id not in visited:
                            visited.add(neighbor.id)
                            entities.append(neighbor)
                            next_level.append(neighbor.id)

                    # Note: In a complete implementation, we'd also collect
                    # the relations between entities here

                current_level = next_level
                if not current_level:
                    break

            return {
                "entities": [e.model_dump() for e in entities],
                "relations": relations,  # Would be populated in full implementation
            }

        except Exception as e:
            logger.error(f"Failed to get session knowledge graph: {e}")
            return {"entities": [], "relations": []}

    async def clear_session_knowledge(self, session_id: str, remove_entities: bool = False) -> bool:
        """
        Clear knowledge graph associations for a session.

        Args:
            session_id: Session identifier
            remove_entities: If True, also remove the session entity itself

        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return False

        try:
            session_entity_id = f"session_{session_id}"

            if remove_entities:
                # Check if delete_entity method exists (SQLite has it, InMemory
                # might not)
                if hasattr(self.graph_store, "delete_entity"):
                    await self.graph_store.delete_entity(session_entity_id)
                    logger.info(f"Removed session entity {session_entity_id}")
                else:
                    # For InMemoryGraphStore, we can't easily delete entities
                    # Just log a warning
                    logger.warning(f"delete_entity not available for {type(self.graph_store).__name__}, " f"session entity {session_entity_id} not removed")

            return True

        except Exception as e:
            logger.error(f"Failed to clear session knowledge: {e}")
            return False


class ContextEngineWithGraph(GraphMemoryMixin):
    """
    ContextEngine extended with graph memory capabilities.

    This class can be used as a standalone context engine with graph support,
    or as a mixin to extend existing ContextEngine instances.

    Example:
        from aiecs.domain.context import ContextEngine
        from aiecs.domain.context.graph_memory import ContextEngineWithGraph
        from aiecs.infrastructure.graph_storage import InMemoryGraphStore

        # Create graph store
        graph_store = InMemoryGraphStore()
        await graph_store.initialize()

        # Create context engine with graph support
        # Note: Actual usage would involve proper inheritance or composition
        context_engine = ContextEngine()
        context_engine.graph_store = graph_store
        await context_engine.initialize()

        # Now you can use graph memory methods
        await context_engine.store_knowledge(session_id, entity)
    """

    def __init__(self, graph_store: Optional[GraphStore] = None):
        """
        Initialize with optional graph store.

        Args:
            graph_store: Optional knowledge graph store
        """
        self.graph_store = graph_store
        logger.info(f"ContextEngineWithGraph initialized with graph_store=" f"{'enabled' if graph_store else 'disabled'}")
