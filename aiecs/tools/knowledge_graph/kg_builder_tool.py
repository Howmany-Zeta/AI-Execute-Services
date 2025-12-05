"""
Knowledge Graph Builder Tool

AIECS tool for building knowledge graphs from text and documents.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import (
    LLMEntityExtractor,
)
from aiecs.application.knowledge_graph.extractors.llm_relation_extractor import (
    LLMRelationExtractor,
)
from aiecs.application.knowledge_graph.builder.graph_builder import (
    GraphBuilder,
)
from aiecs.application.knowledge_graph.builder.document_builder import (
    DocumentGraphBuilder,
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import (
    StructuredDataPipeline,
)
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping,
)


class KGBuilderInput(BaseModel):
    """Input schema for Knowledge Graph Builder Tool (legacy, for execute() method)"""

    action: str = Field(
        ...,
        description="Action to perform: 'build_from_text', 'build_from_document', 'build_from_structured_data', 'get_stats'",
    )
    text: Optional[str] = Field(
        None,
        description="Text to extract knowledge from (for 'build_from_text' action)",
    )
    document_path: Optional[str] = Field(
        None,
        description="Path to document file (for 'build_from_document' action)",
    )
    source: Optional[str] = Field(
        None,
        description="Optional source identifier (document name, URL, etc.)",
    )
    entity_types: Optional[List[str]] = Field(
        None,
        description=("Optional list of entity types to extract " "(e.g., ['Person', 'Company', 'Location'])"),
    )
    data_path: Optional[str] = Field(
        None,
        description="Path to structured data file (CSV, JSON, SPSS, or Excel) for 'build_from_structured_data' action",
    )
    schema_mapping: Optional[Dict[str, Any]] = Field(
        None,
        description="Schema mapping configuration for structured data import (entity_mappings, relation_mappings)",
    )
    relation_types: Optional[List[str]] = Field(
        None,
        description="Optional list of relation types to extract (e.g., ['WORKS_FOR', 'LOCATED_IN'])",
    )


# Schemas for individual operations (used with run_async)
class BuildFromTextSchema(BaseModel):
    """Schema for build_from_text operation"""

    text: str = Field(..., description="Text to extract knowledge from")
    source: Optional[str] = Field(
        default="unknown",
        description="Optional source identifier (document name, URL, etc.)",
    )
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Optional list of entity types to extract (e.g., ['Person', 'Company', 'Location'])",
    )
    relation_types: Optional[List[str]] = Field(
        default=None,
        description="Optional list of relation types to extract (e.g., ['WORKS_FOR', 'LOCATED_IN'])",
    )


class BuildFromDocumentSchema(BaseModel):
    """Schema for build_from_document operation"""

    document_path: str = Field(..., description="Path to document file (PDF, DOCX, TXT, etc.)")
    entity_types: Optional[List[str]] = Field(default=None, description="Optional list of entity types to extract")
    relation_types: Optional[List[str]] = Field(default=None, description="Optional list of relation types to extract")


class GetStatsSchema(BaseModel):
    """Schema for get_stats operation"""

    pass  # No parameters needed


@register_tool("kg_builder")
class KnowledgeGraphBuilderTool(BaseTool):
    """
    Knowledge Graph Builder Tool

    Allows AI agents to build knowledge graphs from text and documents.
    Extracts entities and relations, stores them in a graph database.

    Actions:
    - build_from_text: Extract knowledge from text
    - build_from_document: Extract knowledge from a document (PDF, DOCX, TXT)
    - get_stats: Get statistics about the knowledge graph

    Example Usage:
        ```python
        # Build from text
        result = tool.execute({
            "action": "build_from_text",
            "text": "Alice works at Tech Corp in San Francisco.",
            "source": "conversation_1"
        })

        # Build from document
        result = tool.execute({
            "action": "build_from_document",
            "document_path": "/path/to/research_paper.pdf"
        })

        # Get stats
        stats = tool.execute({
            "action": "get_stats"
        })
        ```
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the Knowledge Graph Builder Tool
        
        Automatically reads from environment variables with KG_BUILDER_ prefix.
        Example: KG_BUILDER_CHUNK_SIZE -> chunk_size
        """

        model_config = SettingsConfigDict(env_prefix="KG_BUILDER_")

        chunk_size: int = Field(
            default=2000,
            description="Chunk size for document processing",
        )
        enable_deduplication: bool = Field(
            default=True,
            description="Enable entity deduplication",
        )
        enable_linking: bool = Field(
            default=True,
            description="Enable entity linking",
        )
        enable_chunking: bool = Field(
            default=True,
            description="Enable document chunking",
        )
        batch_size: int = Field(
            default=100,
            description="Batch size for structured data import",
        )
        skip_errors: bool = Field(
            default=True,
            description="Skip errors during structured data import",
        )

    name: str = "kg_builder"
    description: str = """Build knowledge graphs from text and documents.

    This tool extracts entities (people, companies, locations, etc.) and relations
    between them from text or documents, and stores them in a knowledge graph.

    Use this tool when you need to:
    - Extract structured knowledge from unstructured text
    - Build a knowledge base from documents
    - Understand relationships between entities in text
    - Create a queryable graph of information
    """

    input_schema: type[BaseModel] = KGBuilderInput

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize Knowledge Graph Builder Tool.

        Args:
            config (Dict, optional): Configuration overrides for KG Builder Tool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/kg_builder.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        # Initialize graph store (in-memory for now)
        # In production, this would be configurable (SQLite, PostgreSQL, etc.)
        self.graph_store = None
        self.graph_builder = None
        self.document_builder = None
        self._initialized = False

    async def _initialize(self):
        """Lazy initialization of components"""
        if self._initialized:
            return

        # Initialize graph store
        self.graph_store = InMemoryGraphStore()
        await self.graph_store.initialize()

        # Initialize extractors
        entity_extractor = LLMEntityExtractor()
        relation_extractor = LLMRelationExtractor()

        # Initialize graph builder
        self.graph_builder = GraphBuilder(
            graph_store=self.graph_store,
            entity_extractor=entity_extractor,
            relation_extractor=relation_extractor,
            enable_deduplication=self.config.enable_deduplication,
            enable_linking=self.config.enable_linking,
        )

        # Initialize document builder
        self.document_builder = DocumentGraphBuilder(
            graph_builder=self.graph_builder,
            chunk_size=self.config.chunk_size,
            enable_chunking=self.config.enable_chunking,
        )

        self._initialized = True

    async def _execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the knowledge graph builder tool

        Args:
            **kwargs: Tool input parameters

        Returns:
            Dictionary with results
        """
        # Initialize components
        await self._initialize()

        action = kwargs.get("action")

        if action == "build_from_text":
            return await self._build_from_text(kwargs)
        elif action == "build_from_document":
            return await self._build_from_document(kwargs)
        elif action == "build_from_structured_data":
            return await self._build_from_structured_data(kwargs)
        elif action == "get_stats":
            return await self._get_stats()
        else:
            return {
                "success": False,
                "error": (f"Unknown action: {action}. " f"Supported actions: build_from_text, build_from_document, build_from_structured_data, get_stats"),
            }

    async def _build_from_text(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build knowledge graph from text

        Args:
            kwargs: Tool input parameters

        Returns:
            Build result dictionary
        """
        text = kwargs.get("text")
        if not text:
            return {
                "success": False,
                "error": "Missing required parameter: text",
            }

        source = kwargs.get("source", "unknown")

        # Build graph
        result = await self.graph_builder.build_from_text(text=text, source=source)

        return {
            "success": result.success,
            "entities_added": result.entities_added,
            "relations_added": result.relations_added,
            "entities_linked": result.entities_linked,
            "entities_deduplicated": result.entities_deduplicated,
            "relations_deduplicated": result.relations_deduplicated,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    async def _build_from_document(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build knowledge graph from document

        Args:
            kwargs: Tool input parameters

        Returns:
            Build result dictionary
        """
        document_path = kwargs.get("document_path")
        if not document_path:
            return {
                "success": False,
                "error": "Missing required parameter: document_path",
            }

        # Build graph from document
        result = await self.document_builder.build_from_document(document_path)

        return {
            "success": result.success,
            "document_path": result.document_path,
            "document_type": result.document_type,
            "total_chunks": result.total_chunks,
            "chunks_processed": result.chunks_processed,
            "total_entities_added": result.total_entities_added,
            "total_relations_added": result.total_relations_added,
            "errors": result.errors,
        }

    async def _build_from_structured_data(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build knowledge graph from structured data (CSV, JSON, SPSS, or Excel)

        Args:
            kwargs: Tool input parameters

        Returns:
            Build result dictionary
        """
        data_path = kwargs.get("data_path")
        if not data_path:
            return {
                "success": False,
                "error": "Missing required parameter: data_path",
            }

        schema_mapping_dict = kwargs.get("schema_mapping")
        if not schema_mapping_dict:
            return {
                "success": False,
                "error": "Missing required parameter: schema_mapping",
            }

        try:
            # Parse schema mapping
            entity_mappings = []
            for em_dict in schema_mapping_dict.get("entity_mappings", []):
                entity_mappings.append(EntityMapping(**em_dict))

            relation_mappings = []
            for rm_dict in schema_mapping_dict.get("relation_mappings", []):
                relation_mappings.append(RelationMapping(**rm_dict))

            schema_mapping = SchemaMapping(
                entity_mappings=entity_mappings,
                relation_mappings=relation_mappings,
            )

            # Create structured data pipeline
            pipeline = StructuredDataPipeline(
                mapping=schema_mapping,
                graph_store=self.graph_store,
                batch_size=self.config.batch_size,
                skip_errors=self.config.skip_errors,
            )

            # Import data based on file extension
            if data_path.endswith(".csv"):
                result = await pipeline.import_from_csv(data_path)
            elif data_path.endswith(".json"):
                result = await pipeline.import_from_json(data_path)
            elif data_path.endswith(".sav") or data_path.endswith(".por"):
                result = await pipeline.import_from_spss(data_path)
            elif data_path.endswith(".xlsx") or data_path.endswith(".xls"):
                result = await pipeline.import_from_excel(data_path)
            else:
                return {
                    "success": False,
                    "error": "Unsupported file format. Supported: .csv, .json, .sav, .por, .xlsx, .xls",
                }

            return {
                "success": result.success,
                "data_path": data_path,
                "entities_added": result.entities_added,
                "relations_added": result.relations_added,
                "rows_processed": result.rows_processed,
                "rows_failed": result.rows_failed,
                "duration_seconds": result.duration_seconds,
                "errors": result.errors,
                "warnings": result.warnings,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to import structured data: {str(e)}",
            }

    async def _get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge graph statistics

        Returns:
            Statistics dictionary
        """
        # Handle both async and sync get_stats methods
        if hasattr(self.graph_store.get_stats, "__call__"):
            stats_result = self.graph_store.get_stats()
            # Check if it's a coroutine
            if hasattr(stats_result, "__await__"):
                stats = await stats_result
            else:
                stats = stats_result
        else:
            stats = self.graph_store.get_stats()

        return {"success": True, "stats": stats}

    # Public methods for ToolExecutor integration
    async def build_from_text(
        self,
        text: str,
        source: Optional[str] = "unknown",
        entity_types: Optional[List[str]] = None,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build knowledge graph from text (public method for ToolExecutor)

        Args:
            text: Text to extract knowledge from
            source: Optional source identifier
            entity_types: Optional list of entity types to extract
            relation_types: Optional list of relation types to extract

        Returns:
            Build result dictionary
        """
        await self._initialize()
        return await self._build_from_text(
            {
                "text": text,
                "source": source,
                "entity_types": entity_types,
                "relation_types": relation_types,
            }
        )

    async def build_from_document(
        self,
        document_path: str,
        entity_types: Optional[List[str]] = None,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build knowledge graph from document (public method for ToolExecutor)

        Args:
            document_path: Path to document file
            entity_types: Optional list of entity types to extract
            relation_types: Optional list of relation types to extract

        Returns:
            Build result dictionary
        """
        await self._initialize()
        return await self._build_from_document(
            {
                "document_path": document_path,
                "entity_types": entity_types,
                "relation_types": relation_types,
            }
        )

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge graph statistics (public method for ToolExecutor)

        Returns:
            Statistics dictionary
        """
        await self._initialize()
        return await self._get_stats()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool (public interface)

        Args:
            **kwargs: Tool input parameters

        Returns:
            Dictionary with results
        """
        return await self._execute(**kwargs)

    async def close(self):
        """Clean up resources"""
        if self.graph_store and self._initialized:
            await self.graph_store.close()
