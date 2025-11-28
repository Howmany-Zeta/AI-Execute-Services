"""
Graph Builder - Main Pipeline Orchestrator

Orchestrates the full document-to-graph conversion pipeline.
"""

import asyncio
from typing import List, Optional, Dict, Any, Callable, cast, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import logging

from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.application.knowledge_graph.extractors.base import (
    EntityExtractor,
    RelationExtractor,
)
from aiecs.application.knowledge_graph.fusion.entity_deduplicator import (
    EntityDeduplicator,
)
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker
from aiecs.application.knowledge_graph.fusion.relation_deduplicator import (
    RelationDeduplicator,
)
from aiecs.application.knowledge_graph.validators.relation_validator import (
    RelationValidator,
)

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """
    Result of graph building operation

    Attributes:
        success: Whether build completed successfully
        entities_added: Number of entities added to graph
        relations_added: Number of relations added to graph
        entities_linked: Number of entities linked to existing entities
        entities_deduplicated: Number of entities deduplicated
        relations_deduplicated: Number of relations deduplicated
        errors: List of errors encountered
        warnings: List of warnings
        metadata: Additional metadata about the build
        start_time: When build started
        end_time: When build ended
        duration_seconds: Total duration in seconds
    """

    success: bool = True
    entities_added: int = 0
    relations_added: int = 0
    entities_linked: int = 0
    entities_deduplicated: int = 0
    relations_deduplicated: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0


class GraphBuilder:
    """
    Main pipeline for building knowledge graphs from text

    The pipeline:
    1. Extract entities from text
    2. Deduplicate entities
    3. Link entities to existing graph
    4. Extract relations between entities
    5. Validate relations
    6. Deduplicate relations
    7. Store entities and relations in graph

    Features:
    - Async/parallel processing
    - Progress callbacks
    - Error handling and recovery
    - Provenance tracking
    - Configurable components

    Example::

        # Initialize components
        entity_extractor = LLMEntityExtractor(schema)
        relation_extractor = LLMRelationExtractor(schema)

        # Create builder
        builder = GraphBuilder(
            graph_store=store,
            entity_extractor=entity_extractor,
            relation_extractor=relation_extractor,
            schema=schema
        )

        # Build graph from text
        result = await builder.build_from_text(
            text="Alice works at Tech Corp.",
            source="document_1.pdf"
        )

        print(f"Added {result.entities_added} entities, {result.relations_added} relations")
    """

    def __init__(
        self,
        graph_store: GraphStore,
        entity_extractor: EntityExtractor,
        relation_extractor: RelationExtractor,
        schema: Optional[GraphSchema] = None,
        enable_deduplication: bool = True,
        enable_linking: bool = True,
        enable_validation: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        embedding_client: Optional["LLMClientProtocol"] = None,
    ):
        """
        Initialize graph builder

        Args:
            graph_store: Graph storage to save entities/relations
            entity_extractor: Entity extractor to use
            relation_extractor: Relation extractor to use
            schema: Optional schema for validation
            enable_deduplication: Enable entity/relation deduplication
            enable_linking: Enable linking to existing entities
            enable_validation: Enable relation validation
            progress_callback: Optional callback for progress updates (message, progress_pct)
            embedding_client: Optional custom LLM client for generating embeddings
        """
        self.graph_store = graph_store
        self.entity_extractor = entity_extractor
        self.relation_extractor = relation_extractor
        self.schema = schema
        self.enable_deduplication = enable_deduplication
        self.enable_linking = enable_linking
        self.enable_validation = enable_validation
        self.progress_callback = progress_callback
        self.embedding_client = embedding_client

        # Initialize fusion components
        self.entity_deduplicator = EntityDeduplicator() if enable_deduplication else None
        self.entity_linker = EntityLinker(graph_store) if enable_linking else None
        self.relation_deduplicator = RelationDeduplicator() if enable_deduplication else None
        self.relation_validator = RelationValidator(schema) if enable_validation and schema else None

    @staticmethod
    def from_config(
        graph_store: GraphStore,
        entity_extractor: EntityExtractor,
        relation_extractor: RelationExtractor,
        schema: Optional[GraphSchema] = None,
        enable_deduplication: bool = True,
        enable_linking: bool = True,
        enable_validation: bool = True,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> "GraphBuilder":
        """
        Create GraphBuilder with embedding client resolved from configuration

        This factory method automatically resolves the embedding client from
        the global Settings configuration using LLMClientFactory.

        Args:
            graph_store: Graph storage to save entities/relations
            entity_extractor: Entity extractor to use
            relation_extractor: Relation extractor to use
            schema: Optional schema for validation
            enable_deduplication: Enable entity/relation deduplication
            enable_linking: Enable linking to existing entities
            enable_validation: Enable relation validation
            progress_callback: Optional callback for progress updates

        Returns:
            GraphBuilder instance with configured embedding client

        Example::

            from aiecs.config import get_settings
            from aiecs.llm.factory import LLMClientFactory

            # Register custom embedding provider
            LLMClientFactory.register_custom_provider("my_embedder", my_client)

            # Set environment variable
            os.environ["KG_EMBEDDING_PROVIDER"] = "my_embedder"

            # Create builder with auto-resolved embedding client
            builder = GraphBuilder.from_config(
                graph_store=store,
                entity_extractor=extractor,
                relation_extractor=rel_extractor
            )
        """
        from aiecs.config import get_settings
        from aiecs.llm import resolve_llm_client

        settings = get_settings()

        # Resolve embedding client from configuration
        embedding_client = None
        if settings.kg_embedding_provider:
            try:
                embedding_client = resolve_llm_client(
                    provider=settings.kg_embedding_provider,
                    model=settings.kg_embedding_model,
                )
                logger.info(
                    f"Using embedding provider: {settings.kg_embedding_provider} "
                    f"with model: {settings.kg_embedding_model}"
                )
            except Exception as e:
                logger.warning(f"Failed to resolve embedding client from config: {e}")

        return GraphBuilder(
            graph_store=graph_store,
            entity_extractor=entity_extractor,
            relation_extractor=relation_extractor,
            schema=schema,
            enable_deduplication=enable_deduplication,
            enable_linking=enable_linking,
            enable_validation=enable_validation,
            progress_callback=progress_callback,
            embedding_client=embedding_client,
        )

    async def build_from_text(
        self,
        text: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BuildResult:
        """
        Build knowledge graph from text

        Args:
            text: Input text to process
            source: Optional source identifier (document name, URL, etc.)
            metadata: Optional metadata to attach to entities/relations

        Returns:
            BuildResult with statistics and errors
        """
        result = BuildResult(start_time=datetime.now())

        try:
            self._report_progress("Starting entity extraction", 0.1)

            # Step 1: Extract entities
            entities = await self.entity_extractor.extract_entities(text)

            if not entities:
                result.warnings.append("No entities extracted from text")
                return self._finalize_result(result)

            self._report_progress(f"Extracted {len(entities)} entities", 0.2)

            # Step 2: Deduplicate entities (within this text)
            if self.enable_deduplication and self.entity_deduplicator:
                original_count = len(entities)
                entities = await self.entity_deduplicator.deduplicate(entities)
                result.entities_deduplicated = original_count - len(entities)
                self._report_progress(f"Deduplicated to {len(entities)} entities", 0.3)

            # Step 3: Link entities to existing graph
            linked_entities = []
            new_entities = []

            if self.enable_linking and self.entity_linker:
                self._report_progress("Linking entities to graph", 0.4)
                link_results = await self.entity_linker.link_entities(entities)

                for link_result in link_results:
                    if link_result.linked:
                        linked_entities.append(link_result.existing_entity)
                        result.entities_linked += 1
                    else:
                        new_entities.append(link_result.new_entity)
            else:
                new_entities = entities

            # Combine linked and new entities for relation extraction
            all_entities_with_none = linked_entities + new_entities
            # Filter out None values for relation extraction
            all_entities = [e for e in all_entities_with_none if e is not None]

            # Step 4: Extract relations
            if len(all_entities) >= 2:
                self._report_progress(
                    f"Extracting relations from {len(all_entities)} entities",
                    0.5,
                )
                relations = await self.relation_extractor.extract_relations(text, all_entities)
                self._report_progress(f"Extracted {len(relations)} relations", 0.6)
            else:
                relations = []
                result.warnings.append("Not enough entities for relation extraction")

            # Step 5: Validate relations
            valid_relations = relations
            if self.enable_validation and self.relation_validator and relations:
                self._report_progress("Validating relations", 0.7)
                valid_relations = self.relation_validator.filter_valid_relations(relations, all_entities)
                invalid_count = len(relations) - len(valid_relations)
                if invalid_count > 0:
                    result.warnings.append(f"{invalid_count} relations failed validation")

            # Step 6: Deduplicate relations
            if self.enable_deduplication and self.relation_deduplicator and valid_relations:
                original_count = len(valid_relations)
                valid_relations = await self.relation_deduplicator.deduplicate(valid_relations)
                result.relations_deduplicated = original_count - len(valid_relations)
                self._report_progress(f"Deduplicated to {len(valid_relations)} relations", 0.8)

            # Step 7: Generate embeddings for entities
            if self.embedding_client and new_entities:
                self._report_progress("Generating embeddings for entities", 0.85)
                await self._generate_embeddings_for_entities(new_entities)

            # Step 8: Store in graph
            self._report_progress("Storing entities and relations in graph", 0.9)

            # Add provenance metadata
            if source or metadata:
                provenance = {"source": source} if source else {}
                if metadata:
                    provenance.update(metadata)

                # Add provenance to entities
                for entity in new_entities:
                    if not entity.properties:
                        entity.properties = {}
                    entity.properties["_provenance"] = provenance

                # Add provenance to relations
                for relation in valid_relations:
                    if not relation.properties:
                        relation.properties = {}
                    relation.properties["_provenance"] = provenance

            # Store entities
            for entity in new_entities:
                await self.graph_store.add_entity(entity)
                result.entities_added += 1

            # Store relations
            for relation in valid_relations:
                await self.graph_store.add_relation(relation)
                result.relations_added += 1

            self._report_progress("Build complete", 1.0)

        except Exception as e:
            result.success = False
            result.errors.append(f"Build failed: {str(e)}")

        return self._finalize_result(result)

    async def build_batch(
        self,
        texts: List[str],
        sources: Optional[List[str]] = None,
        parallel: bool = True,
        max_parallel: int = 5,
    ) -> List[BuildResult]:
        """
        Build graph from multiple texts in batch

        Args:
            texts: List of texts to process
            sources: Optional list of source identifiers (same length as texts)
            parallel: Process in parallel (default: True)
            max_parallel: Maximum parallel tasks (default: 5)

        Returns:
            List of BuildResult objects (one per text)
        """
        if sources and len(sources) != len(texts):
            raise ValueError("sources list must match texts list length")

        if not sources:
            sources = [f"text_{i}" for i in range(len(texts))]

        if parallel:
            # Process in parallel with semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_parallel)

            async def process_one(text, source):
                async with semaphore:
                    return await self.build_from_text(text, source)

            tasks = [process_one(text, source) for text, source in zip(texts, sources)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_result = BuildResult(success=False)
                    error_result.errors.append(str(result))
                    results[i] = error_result

            return cast(List[BuildResult], results)
        else:
            # Process sequentially
            sequential_results: List[BuildResult] = []
            for text, source in zip(texts, sources):
                result = await self.build_from_text(text, source)
                sequential_results.append(result)
            return sequential_results

    def _report_progress(self, message: str, progress: float):
        """
        Report progress via callback

        Args:
            message: Progress message
            progress: Progress percentage (0.0-1.0)
        """
        if self.progress_callback:
            try:
                self.progress_callback(message, progress)
            except Exception as e:
                # Don't let callback errors break the pipeline
                print(f"Warning: Progress callback error: {e}")

    def _finalize_result(self, result: BuildResult) -> BuildResult:
        """
        Finalize build result with timing information

        Args:
            result: BuildResult to finalize

        Returns:
            Finalized BuildResult
        """
        result.end_time = datetime.now()
        if result.start_time:
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        return result

    async def _generate_embeddings_for_entities(
        self, entities: List[Any], model: Optional[str] = None
    ) -> None:
        """
        Generate embeddings for entities using the configured embedding client

        Args:
            entities: List of entities to generate embeddings for
            model: Optional model name for embedding generation

        Note:
            This method modifies entities in-place by setting their embedding attribute.
            If no embedding client is configured, entities will not have embeddings.
        """
        if not self.embedding_client or not entities:
            return

        try:
            # Prepare texts for embedding (use entity name or string representation)
            texts = []
            for entity in entities:
                # Try to get a meaningful text representation
                name = entity.properties.get("name") if entity.properties else None
                if name:
                    text = f"{entity.entity_type}: {name}"
                else:
                    text = f"{entity.entity_type}: {entity.id}"
                texts.append(text)

            # Generate embeddings
            embeddings = await self.embedding_client.get_embeddings(texts, model=model)

            # Assign embeddings to entities
            for entity, embedding in zip(entities, embeddings):
                entity.embedding = embedding

            logger.debug(f"Generated embeddings for {len(entities)} entities")

        except NotImplementedError:
            logger.debug("Embedding client does not support get_embeddings()")
        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
