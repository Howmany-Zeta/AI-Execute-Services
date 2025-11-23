"""
Base Abstract Classes for Entity and Relation Extraction

Defines the interface for extracting entities and relations from text.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class EntityExtractor(ABC):
    """
    Abstract base class for entity extraction

    Entity extractors take text input and return a list of entities found in the text.
    Different implementations can use different methods (LLM, NER, rule-based, etc.).

    Example:
        ```python
        extractor = LLMEntityExtractor(llm_client, schema)
        entities = await extractor.extract_entities(
            "Alice works at Tech Corp in San Francisco"
        )
        # Returns: [Entity(Person: Alice), Entity(Company: Tech Corp), ...]
        ```
    """

    @abstractmethod
    async def extract_entities(self, text: str, entity_types: Optional[List[str]] = None, **kwargs) -> List[Entity]:
        """
        Extract entities from text

        Args:
            text: Input text to extract entities from
            entity_types: Optional list of entity types to extract (e.g., ["Person", "Company"])
                         If None, extract all types supported by the extractor
            **kwargs: Additional extractor-specific parameters

        Returns:
            List of Entity objects found in the text

        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If extraction fails
        """


class RelationExtractor(ABC):
    """
    Abstract base class for relation extraction

    Relation extractors take text and a list of entities, and return relations
    (edges) between those entities. This is a two-stage extraction process:
    entities must be extracted first, then relations between them.

    Example:
        ```python
        extractor = LLMRelationExtractor(llm_client, schema)

        # Entities already extracted
        alice = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        tech_corp = Entity(id="e2", entity_type="Company", properties={"name": "Tech Corp"})

        relations = await extractor.extract_relations(
            text="Alice works at Tech Corp",
            entities=[alice, tech_corp]
        )
        # Returns: [Relation(alice -[WORKS_FOR]-> tech_corp)]
        ```
    """

    @abstractmethod
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
            text: Input text containing the entities
            entities: List of entities already extracted from this text
            relation_types: Optional list of relation types to extract (e.g., ["WORKS_FOR", "KNOWS"])
                           If None, extract all types supported by the extractor
            **kwargs: Additional extractor-specific parameters

        Returns:
            List of Relation objects found between the entities

        Raises:
            ValueError: If text is empty or entities list is empty
            RuntimeError: If extraction fails
        """
