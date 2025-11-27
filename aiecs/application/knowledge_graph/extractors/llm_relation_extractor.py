"""
LLM-based Relation Extractor

Extracts relations between entities using Large Language Models.
"""

import json
import uuid
from typing import List, Optional
from aiecs.application.knowledge_graph.extractors.base import RelationExtractor
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.llm import get_llm_manager, AIProvider, LLMClientManager


class LLMRelationExtractor(RelationExtractor):
    """
    Extract relations between entities using LLMs

    Given text and a list of entities, identifies relationships between them.
    Uses LLMs to understand semantic relationships and extract structured relations.

    Features:
    - Schema-aware extraction (uses relation types from schema)
    - Entity-aware (only extracts relations between known entities)
    - Property extraction (relation properties/attributes)
    - Confidence scoring
    - Directional relation support

    Example:
        ```python
        extractor = LLMRelationExtractor(schema=graph_schema)

        alice = Entity(id="e1", type="Person", properties={"name": "Alice"})
        tech_corp = Entity(id="e2", type="Company", properties={"name": "Tech Corp"})

        relations = await extractor.extract_relations(
            text="Alice works as a senior engineer at Tech Corp.",
            entities=[alice, tech_corp]
        )
        # Returns: [
        #   Relation(
        #     source_id="e1",
        #     target_id="e2",
        #     relation_type="WORKS_FOR",
        #     properties={"title": "senior engineer"}
        #   )
        # ]
        ```
    """

    def __init__(
        self,
        schema: Optional[GraphSchema] = None,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = 2000,
    ):
        """
        Initialize LLM relation extractor

        Args:
            schema: Optional GraphSchema to guide extraction
            provider: LLM provider (default: Vertex AI)
            model: Specific model to use
            temperature: LLM temperature (low for deterministic extraction)
            max_tokens: Maximum tokens in response
        """
        self.schema = schema
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm_manager: Optional[LLMClientManager] = None  # Lazy-loaded in async methods

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        relation_types: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Relation]:
        """
        Extract relations from text given known entities

        Args:
            text: Input text containing entities
            entities: List of entities already extracted
            relation_types: Optional filter for specific relation types
            **kwargs: Additional parameters

        Returns:
            List of extracted Relation objects

        Raises:
            ValueError: If text or entities are empty
            RuntimeError: If LLM extraction fails
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        if not entities or len(entities) < 2:
            # Need at least 2 entities to have a relation
            return []

        # Lazy-load LLM manager
        if self._llm_manager is None:
            self._llm_manager = await get_llm_manager()

        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, entities, relation_types)

        # Call LLM
        try:
            response = await self._llm_manager.generate_text(
                messages=prompt,
                provider=self.provider,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse LLM response to Relation objects
            relations = self._parse_llm_response(response.content, entities)

            return relations

        except Exception as e:
            raise RuntimeError(f"LLM relation extraction failed: {str(e)}") from e

    def _build_extraction_prompt(
        self,
        text: str,
        entities: List[Entity],
        relation_types: Optional[List[str]] = None,
    ) -> str:
        """
        Build prompt for LLM relation extraction

        The prompt includes:
        1. Task description
        2. List of entities to consider
        3. Relation types to extract (from schema)
        4. Output format specification
        5. The text to analyze

        Args:
            text: Input text
            entities: List of known entities
            relation_types: Optional filter for relation types

        Returns:
            Formatted prompt string
        """
        # Build entity reference list
        entity_list = []
        entity_index = {}
        for idx, entity in enumerate(entities):
            entity_name = self._get_entity_name(entity)
            entity_list.append(f"  [{idx}] {entity.entity_type}: {entity_name} (ID: {entity.id})")
            entity_index[entity.id] = idx

        entities_section = "\n".join(entity_list)

        # Build relation type descriptions
        types_to_extract = []
        if self.schema:
            available_types = self.schema.get_relation_type_names()
            if relation_types:
                types_to_extract = [t for t in relation_types if t in available_types]
            else:
                types_to_extract = available_types
        elif relation_types:
            types_to_extract = relation_types
        else:
            # No schema, use common relation types
            types_to_extract = [
                "WORKS_FOR",
                "LOCATED_IN",
                "PART_OF",
                "KNOWS",
                "OWNS",
                "MANAGES",
                "PRODUCES",
                "RELATED_TO",
            ]

        # Build relation type descriptions
        relation_descriptions = []
        for rel_type in types_to_extract:
            if self.schema and self.schema.has_relation_type(rel_type):
                schema_rel = self.schema.get_relation_type(rel_type)
                if schema_rel is not None:
                    desc = schema_rel.description or f"'{rel_type}' relation"
                    relation_descriptions.append(f"- {rel_type}: {desc}")
                else:
                    relation_descriptions.append(f"- {rel_type}: Extract this type of relationship")
            else:
                relation_descriptions.append(f"- {rel_type}: Extract this type of relationship")

        relations_section = "\n".join(relation_descriptions)

        # Build prompt
        prompt = f"""You are an expert at extracting relationships between entities from text.

Given the following entities:
{entities_section}

Extract all relationships between these entities from the text.

Allowed relation types:
{relations_section}

For each relation, provide:
1. source_id: ID of the source entity (from list above)
2. target_id: ID of the target entity (from list above)
3. relation_type: Type of relation (one of the allowed types)
4. properties: Optional dictionary of relation properties (e.g., since="2020", role="engineer")
5. confidence: Your confidence in this extraction (0.0 to 1.0)

Return ONLY a valid JSON array with this structure:
[
  {{
    "source_id": "entity_id_here",
    "target_id": "entity_id_here",
    "relation_type": "RELATION_TYPE",
    "properties": {{"property1": "value1"}},
    "confidence": 0.95
  }}
]

Important:
- Only extract relations that are explicitly stated or strongly implied in the text
- Use the exact entity IDs from the list above
- Relations should be directional (source -> target matters)
- If unsure about a property, omit it
- Return empty array [] if no relations found

Text to analyze:
\"\"\"{text}\"\"\"

JSON output:"""

        return prompt

    def _parse_llm_response(self, response_text: str, entities: List[Entity]) -> List[Relation]:
        """
        Parse LLM response to Relation objects

        Expected JSON format:
        [
          {
            "source_id": "e1",
            "target_id": "e2",
            "relation_type": "WORKS_FOR",
            "properties": {"title": "engineer"},
            "confidence": 0.95
          }
        ]

        Args:
            response_text: LLM response string
            entities: List of entities for validation

        Returns:
            List of Relation objects
        """
        relations = []
        entity_ids = {e.id for e in entities}

        try:
            # Extract JSON from response
            json_str = self._extract_json_from_text(response_text)

            # Parse JSON
            extracted_data = json.loads(json_str)

            if not isinstance(extracted_data, list):
                extracted_data = [extracted_data]

            # Convert to Relation objects
            for item in extracted_data:
                source_id = item.get("source_id")
                target_id = item.get("target_id")
                relation_type = item.get("relation_type")
                properties = item.get("properties", {})
                confidence = item.get("confidence", 0.5)

                # Validate required fields
                if not source_id or not target_id:
                    continue
                if not relation_type:  # relation_type is required and cannot be None
                    continue
                if source_id not in entity_ids or target_id not in entity_ids:
                    # LLM hallucinated entity IDs
                    continue
                if source_id == target_id:
                    # Self-loop, skip
                    continue

                # Generate unique ID
                relation_id = str(uuid.uuid4())

                # Create Relation
                relation = Relation(
                    id=relation_id,
                    relation_type=relation_type,
                    source_id=source_id,
                    target_id=target_id,
                    properties=properties,
                )

                # Store confidence
                relation.properties["_extraction_confidence"] = confidence

                relations.append(relation)

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {response_text[:200]}...")
            return []

        return relations

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON array from text"""
        # Find JSON array boundaries
        start = text.find("[")
        end = text.rfind("]") + 1

        if start != -1 and end > start:
            return text[start:end]

        # Try single object
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end > start:
            return text[start:end]

        return text

    def _get_entity_name(self, entity: Entity) -> str:
        """Extract entity name from properties"""
        return entity.properties.get("name") or entity.properties.get("title") or entity.properties.get("text") or f"{entity.entity_type}_{entity.id[:8]}"
