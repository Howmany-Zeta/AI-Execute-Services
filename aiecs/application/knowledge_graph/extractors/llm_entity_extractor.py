"""
LLM-based Entity Extractor

Extracts entities from text using Large Language Models (GPT-4, Gemini, etc.).
Uses AIECS's LLM client infrastructure for provider-agnostic extraction.
"""

import json
import uuid
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from aiecs.application.knowledge_graph.extractors.base import EntityExtractor
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.llm import get_llm_manager, AIProvider, LLMClientManager, LLMClientFactory

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol


class LLMEntityExtractor(EntityExtractor):
    """
    Extract entities using Large Language Models

    This extractor uses LLMs (like GPT-4, Gemini) to identify and extract entities
    from text. It's schema-aware and can extract custom entity types with properties.

    Features:
    - Schema-guided extraction (tells LLM what entity types to look for)
    - Property extraction (not just entity names, but also attributes)
    - Confidence scoring (LLM provides confidence for each entity)
    - Configurable LLM provider (Vertex AI default, configurable)

    Example:
        ```python
        from aiecs.llm import AIProvider

        extractor = LLMEntityExtractor(
            schema=graph_schema,
            provider=AIProvider.VERTEX,
            model="gemini-pro"
        )

        entities = await extractor.extract_entities(
            "Alice, a 30-year-old data scientist, works at Tech Corp."
        )
        # Returns: [
        #   Entity(type="Person", properties={"name": "Alice", "age": 30, "occupation": "data scientist"}),
        #   Entity(type="Company", properties={"name": "Tech Corp"})
        # ]
        ```
    """

    def __init__(
        self,
        schema: Optional[GraphSchema] = None,
        provider: Optional[Union[AIProvider, str]] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,  # Low temperature for more deterministic extraction
        max_tokens: Optional[int] = 2000,
        llm_client: Optional["LLMClientProtocol"] = None,
    ):
        """
        Initialize LLM entity extractor

        Args:
            schema: Optional GraphSchema to guide extraction (provides entity types and properties)
            provider: LLM provider to use (default: Vertex AI via AIECS configuration)
                     Can be AIProvider enum or custom provider name string
            model: Specific model to use (default: from AIECS configuration)
            temperature: LLM temperature (0.1 = more deterministic, good for extraction)
            max_tokens: Maximum tokens in response
            llm_client: Optional custom LLM client implementing LLMClientProtocol
                       If provided, this client will be used directly instead of creating one via provider
        """
        self.schema = schema
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm_client = llm_client
        self._llm_manager: Optional[LLMClientManager] = None  # Lazy-loaded in async methods

    @staticmethod
    def from_config(
        schema: Optional[GraphSchema] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> "LLMEntityExtractor":
        """
        Create LLMEntityExtractor from configuration.

        This method resolves the LLM client from the provider name using LLMClientFactory,
        supporting both standard and custom providers.

        Args:
            schema: Optional GraphSchema to guide extraction
            provider: LLM provider name (standard or custom)
            model: Specific model to use
            temperature: LLM temperature
            max_tokens: Maximum tokens in response

        Returns:
            LLMEntityExtractor instance with resolved client

        Example:
            ```python
            # Using standard provider
            extractor = LLMEntityExtractor.from_config(
                provider="OpenAI",
                model="gpt-4",
                temperature=0.1
            )

            # Using custom provider
            LLMClientFactory.register_custom_provider("my-llm", custom_client)
            extractor = LLMEntityExtractor.from_config(
                provider="my-llm",
                model="custom-model"
            )
            ```
        """
        from aiecs.config import get_settings

        settings = get_settings()

        # Use config values if not provided
        if provider is None:
            provider = settings.kg_entity_extraction_llm_provider or None
        if model is None:
            model = settings.kg_entity_extraction_llm_model or None
        if temperature is None:
            temperature = settings.kg_entity_extraction_temperature
        if max_tokens is None:
            max_tokens = settings.kg_entity_extraction_max_tokens

        # Resolve client from provider name if provider is specified
        llm_client = None
        if provider:
            client = LLMClientFactory.get_client(provider)
            # Cast to LLMClientProtocol since BaseLLMClient implements the protocol
            from typing import cast
            from aiecs.llm.protocols import LLMClientProtocol
            llm_client = cast(LLMClientProtocol, client) if client else None
        else:
            llm_client = None

        return LLMEntityExtractor(
            schema=schema,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            llm_client=llm_client,
        )

    async def extract_entities(self, text: str, entity_types: Optional[List[str]] = None, **kwargs) -> List[Entity]:
        """
        Extract entities from text using LLM

        Args:
            text: Input text to extract entities from
            entity_types: Optional filter for specific entity types
            **kwargs: Additional parameters (e.g., custom prompt, examples)

        Returns:
            List of extracted Entity objects

        Raises:
            ValueError: If text is empty
            RuntimeError: If LLM extraction fails
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, entity_types)

        # Call LLM
        try:
            # Use custom client if provided
            if self.llm_client is not None:
                # Convert string prompt to list of LLMMessage
                from aiecs.llm.clients.base_client import LLMMessage
                messages = [LLMMessage(role="user", content=prompt)]
                response = await self.llm_client.generate_text(
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            # Otherwise use LLM manager with provider
            else:
                # Lazy-load LLM manager
                if self._llm_manager is None:
                    self._llm_manager = await get_llm_manager()

                response = await self._llm_manager.generate_text(
                    messages=prompt,
                    provider=self.provider,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

            # Parse LLM response to Entity objects
            entities = self._parse_llm_response(response.content)

            return entities

        except Exception as e:
            raise RuntimeError(f"LLM entity extraction failed: {str(e)}") from e

    def _build_extraction_prompt(self, text: str, entity_types: Optional[List[str]] = None) -> str:
        """
        Build prompt for LLM entity extraction

        The prompt is structured to:
        1. Explain the task (entity extraction)
        2. Provide entity type schemas (if available)
        3. Request JSON output format
        4. Include the text to extract from

        Args:
            text: Input text
            entity_types: Optional filter for entity types

        Returns:
            Formatted prompt string
        """
        # Determine which entity types to extract
        types_to_extract = []
        if self.schema:
            available_types = self.schema.get_entity_type_names()
            if entity_types:
                # Filter to requested types that exist in schema
                types_to_extract = [t for t in entity_types if t in available_types]
            else:
                # Use all types from schema
                types_to_extract = available_types
        elif entity_types:
            # No schema, but user specified types
            types_to_extract = entity_types
        else:
            # No schema and no filter - use common types
            types_to_extract = [
                "Person",
                "Organization",
                "Location",
                "Event",
                "Product",
            ]

        # Build entity type descriptions
        type_descriptions = []
        for entity_type in types_to_extract:
            if self.schema and self.schema.has_entity_type(entity_type):
                # Use schema definition
                schema_type = self.schema.get_entity_type(entity_type)
                if schema_type is not None:
                    properties = list(schema_type.properties.keys()) if schema_type.properties else []
                    prop_str = ", ".join(properties) if properties else "any relevant properties"
                    desc = f"- {entity_type}: {schema_type.description or 'Extract properties: ' + prop_str}"
                    type_descriptions.append(desc)
                else:
                    type_descriptions.append(f"- {entity_type}: Extract name and any relevant properties")
            else:
                # Generic description
                type_descriptions.append(f"- {entity_type}: Extract name and any relevant properties")

        types_description = "\n".join(type_descriptions)

        # Build prompt
        prompt = f"""You are an expert at extracting structured entities from text.

Extract entities of the following types from the text:
{types_description}

For each entity, provide:
1. type: The entity type (one of the types listed above)
2. properties: A dictionary of properties (e.g., name, age, location, etc.)
3. confidence: Your confidence in this extraction (0.0 to 1.0)

Return ONLY a valid JSON array with this structure:
[
  {{
    "type": "EntityType",
    "properties": {{"property1": "value1", "property2": "value2"}},
    "confidence": 0.95
  }}
]

Important:
- Extract ALL entities you find of the specified types
- Include as many relevant properties as you can find
- Use consistent property names (e.g., "name" not "title" or "full_name")
- If unsure about a property, omit it rather than guessing
- Confidence should reflect how certain you are about the entity and its properties

Text to extract from:
\"\"\"{text}\"\"\"

JSON output:"""

        return prompt

    def _parse_llm_response(self, response_text: str) -> List[Entity]:
        """
        Parse LLM response to Entity objects

        Expected JSON format:
        [
          {"type": "Person", "properties": {"name": "Alice", "age": 30}, "confidence": 0.95},
          {"type": "Company", "properties": {"name": "Tech Corp"}, "confidence": 0.90}
        ]

        Args:
            response_text: LLM response string (should be JSON)

        Returns:
            List of Entity objects
        """
        entities = []

        try:
            # Extract JSON from response (LLM might include extra text)
            json_str = self._extract_json_from_text(response_text)

            # Parse JSON
            extracted_data = json.loads(json_str)

            if not isinstance(extracted_data, list):
                # Sometimes LLM returns single object instead of array
                extracted_data = [extracted_data]

            # Convert to Entity objects
            for item in extracted_data:
                entity_type = item.get("type", "Unknown")
                properties = item.get("properties", {})
                confidence = item.get("confidence", 0.5)

                # Generate unique ID
                entity_id = self._generate_entity_id(entity_type, properties)

                # Create Entity
                entity = Entity(
                    id=entity_id,
                    entity_type=entity_type,
                    properties=properties,
                )

                # Store confidence in properties for later use
                entity.properties["_extraction_confidence"] = confidence

                entities.append(entity)

        except json.JSONDecodeError as e:
            # Log error but don't fail completely
            # In production, you might want to retry or use fallback
            print(f"Warning: Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {response_text[:200]}...")
            return []

        return entities

    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON array from text (handles cases where LLM includes extra text)

        Args:
            text: Response text that may contain JSON

        Returns:
            Extracted JSON string
        """
        # Find JSON array boundaries
        start = text.find("[")
        end = text.rfind("]") + 1

        if start != -1 and end > start:
            return text[start:end]

        # Try to find JSON object (single entity)
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end > start:
            return text[start:end]

        # No JSON found, return original
        return text

    def _generate_entity_id(self, entity_type: str, properties: Dict[str, Any]) -> str:
        """
        Generate a unique ID for an entity

        Uses entity type + key property (usually "name") to create deterministic ID,
        with fallback to UUID for uniqueness.

        Args:
            entity_type: Entity type name
            properties: Entity properties

        Returns:
            Unique entity ID string
        """
        # Try to use name for deterministic ID
        name = properties.get("name") or properties.get("title") or properties.get("id")

        if name:
            # Create deterministic ID from type + name
            # Normalize to lowercase and remove spaces
            normalized = f"{entity_type}_{name}".lower().replace(" ", "_")
            # Add short hash for uniqueness
            import hashlib

            hash_suffix = hashlib.md5(normalized.encode()).hexdigest()[:8]
            return f"{normalized}_{hash_suffix}"
        else:
            # No name property, use UUID
            return f"{entity_type.lower()}_{uuid.uuid4().hex[:12]}"
