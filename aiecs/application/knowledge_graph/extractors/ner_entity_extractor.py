"""
spaCy NER-based Entity Extractor

Extracts entities using spaCy's Named Entity Recognition.
Fast, offline, and cost-free alternative to LLM extraction.
"""

from typing import List, Optional
import spacy
from spacy.language import Language

from aiecs.application.knowledge_graph.extractors.base import EntityExtractor
from aiecs.domain.knowledge_graph.models.entity import Entity


class NEREntityExtractor(EntityExtractor):
    """
    Extract entities using spaCy Named Entity Recognition

    This extractor uses spaCy's pre-trained NER models to identify entities.
    It's fast, free, and works offline, but limited to standard NER types.

    Features:
    - Fast extraction (no API calls)
    - Works offline
    - No cost
    - Standard NER types (PERSON, ORG, GPE, LOC, DATE, etc.)

    Limitations:
    - Only standard entity types (no custom types)
    - Limited property extraction (mainly just entity text)
    - Lower quality than LLM extraction

    Use Cases:
    - Development and testing
    - Cost-sensitive scenarios
    - High-volume extraction where LLM is too expensive
    - Baseline for comparison

    Example:
        ```python
        extractor = NEREntityExtractor(model="en_core_web_sm")

        entities = await extractor.extract_entities(
            "Alice works at Tech Corp in San Francisco."
        )
        # Returns: [
        #   Entity(type="Person", properties={"name": "Alice", "text": "Alice"}),
        #   Entity(type="Organization", properties={"name": "Tech Corp", "text": "Tech Corp"}),
        #   Entity(type="Location", properties={"name": "San Francisco", "text": "San Francisco"})
        # ]
        ```
    """

    # Mapping from spaCy NER labels to generic entity types
    LABEL_MAPPING = {
        "PERSON": "Person",
        "PER": "Person",
        "ORG": "Organization",
        "ORGANIZATION": "Organization",
        "GPE": "Location",  # Geo-Political Entity
        "LOC": "Location",
        "LOCATION": "Location",
        "FAC": "Facility",
        "FACILITY": "Facility",
        "PRODUCT": "Product",
        "EVENT": "Event",
        "WORK_OF_ART": "WorkOfArt",
        "LAW": "Law",
        "LANGUAGE": "Language",
        "DATE": "Date",
        "TIME": "Time",
        "PERCENT": "Percentage",
        "MONEY": "Money",
        "QUANTITY": "Quantity",
        "ORDINAL": "Ordinal",
        "CARDINAL": "Cardinal",
    }

    def __init__(
        self,
        model: str = "en_core_web_sm",
        disable_components: Optional[List[str]] = None,
    ):
        """
        Initialize NER entity extractor

        Args:
            model: spaCy model name (default: "en_core_web_sm")
                   Available models:
                   - en_core_web_sm: Small English model (~13MB)
                   - en_core_web_md: Medium English model (~40MB)
                   - en_core_web_lg: Large English model (~560MB)
            disable_components: spaCy pipeline components to disable (for speed)
                              Default: disable all except NER
        """
        self.model_name = model

        try:
            # Load spaCy model
            if disable_components is None:
                # Disable everything except NER for speed
                disable_components = [
                    "tok2vec",
                    "tagger",
                    "parser",
                    "attribute_ruler",
                    "lemmatizer",
                ]

            self.nlp: Language = spacy.load(model, disable=disable_components)
        except OSError as e:
            raise RuntimeError(f"spaCy model '{model}' not found. " f"Install it with: python -m spacy download {model}") from e

    async def extract_entities(self, text: str, entity_types: Optional[List[str]] = None, **kwargs) -> List[Entity]:
        """
        Extract entities from text using spaCy NER

        Args:
            text: Input text to extract entities from
            entity_types: Optional filter for specific entity types
                         (will be matched against LABEL_MAPPING values)
            **kwargs: Additional parameters (unused for NER)

        Returns:
            List of extracted Entity objects

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        # Process text with spaCy
        doc = self.nlp(text)

        # Extract entities
        entities = []
        seen_texts = set()  # Simple deduplication within same text

        for ent in doc.ents:
            # Map spaCy label to generic entity type
            entity_type = self.LABEL_MAPPING.get(ent.label_, ent.label_)

            # Filter by entity type if requested
            if entity_types and entity_type not in entity_types:
                continue

            # Simple deduplication: skip if we've seen this exact text already
            entity_text = ent.text.strip()
            if entity_text in seen_texts:
                continue
            seen_texts.add(entity_text)

            # Create entity
            entity = Entity(
                id=self._generate_entity_id(entity_type, entity_text),
                entity_type=entity_type,
                properties={
                    "name": entity_text,
                    "text": entity_text,
                    "label": ent.label_,  # Original spaCy label
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                    "_extraction_confidence": self._estimate_confidence(ent),
                },
            )

            entities.append(entity)

        return entities

    def _generate_entity_id(self, entity_type: str, text: str) -> str:
        """
        Generate a unique ID for an entity

        Args:
            entity_type: Entity type name
            text: Entity text

        Returns:
            Unique entity ID string
        """
        # Create deterministic ID from type + text
        normalized = f"{entity_type}_{text}".lower().replace(" ", "_")
        # Add short hash for uniqueness
        import hashlib

        hash_suffix = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"{normalized}_{hash_suffix}"

    def _estimate_confidence(self, ent) -> float:
        """
        Estimate confidence for NER extraction

        spaCy doesn't provide confidence scores directly, so we use heuristics:
        - Longer entities are generally more confident
        - Entities with more context are more confident
        - Capitalized entities (proper nouns) are more confident

        Args:
            ent: spaCy entity

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence
        confidence = 0.7

        # Adjust based on entity length
        if len(ent.text) > 20:
            confidence += 0.1
        elif len(ent.text) < 3:
            confidence -= 0.2

        # Adjust based on capitalization (proper nouns)
        if ent.text[0].isupper():
            confidence += 0.1

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def get_supported_types(self) -> List[str]:
        """
        Get list of entity types that this extractor can produce

        Returns:
            List of entity type names
        """
        return list(set(self.LABEL_MAPPING.values()))

    def get_available_labels(self) -> List[str]:
        """
        Get list of NER labels available in the loaded model

        Returns:
            List of spaCy NER labels
        """
        ner_pipe = self.nlp.get_pipe("ner")
        # spaCy NER pipe has labels attribute
        return ner_pipe.labels if hasattr(ner_pipe, "labels") else []  # type: ignore[attr-defined]
