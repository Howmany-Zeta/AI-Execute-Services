"""
Query Intent Classifier

Classifies query intent to select the optimal retrieval strategy for knowledge graph queries.
Uses a lightweight LLM to determine the best retrieval approach based on query characteristics.
"""

import logging
from typing import Optional, Dict, TYPE_CHECKING
from aiecs.application.knowledge_graph.retrieval.strategy_types import RetrievalStrategy

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol

logger = logging.getLogger(__name__)


class QueryIntentClassifier:
    """
    Classifies query intent to select optimal retrieval strategy.

    Uses a lightweight LLM to analyze query characteristics and determine
    the best retrieval strategy for knowledge graph queries.

    Features:
    - LLM-based intent classification
    - Result caching for performance
    - Fallback to rule-based classification

    Example:
        ```python
        from aiecs.llm import LLMClientFactory

        # Create classifier with custom LLM
        custom_client = LLMClientFactory.get_client("gpt-3.5-turbo")
        classifier = QueryIntentClassifier(llm_client=custom_client)

        # Classify query
        strategy = await classifier.classify_intent("How is Alice connected to Bob?")
        # Returns: RetrievalStrategy.MULTI_HOP
        ```
    """

    def __init__(
        self,
        llm_client: Optional["LLMClientProtocol"] = None,
        enable_caching: bool = True,
    ):
        """
        Initialize query intent classifier.

        Args:
            llm_client: Optional LLM client for classification
                       If None, falls back to rule-based classification
            enable_caching: Whether to cache classification results
        """
        self.llm_client = llm_client
        self.enable_caching = enable_caching
        self._cache: Dict[str, RetrievalStrategy] = {}

    async def classify_intent(self, query: str) -> RetrievalStrategy:
        """
        Classify query intent and return optimal retrieval strategy.

        Args:
            query: Query string to classify

        Returns:
            RetrievalStrategy enum value

        Raises:
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Check cache first
        if self.enable_caching and query in self._cache:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return self._cache[query]

        # Use LLM classification if client is available
        if self.llm_client is not None:
            try:
                strategy = await self._classify_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}, falling back to rule-based")
                strategy = self._classify_with_rules(query)
        else:
            # Fall back to rule-based classification
            strategy = self._classify_with_rules(query)

        # Cache result
        if self.enable_caching:
            self._cache[query] = strategy

        return strategy

    async def _classify_with_llm(self, query: str) -> RetrievalStrategy:
        """
        Classify query using LLM.

        Args:
            query: Query string

        Returns:
            RetrievalStrategy enum value
        """
        from aiecs.llm import LLMMessage

        # Build classification prompt
        prompt = f"""Classify the following knowledge graph query into one of these retrieval strategies:

1. VECTOR_SEARCH - For semantic similarity queries (e.g., "Find similar entities", "What's related to X?")
2. MULTI_HOP - For relationship/connection queries (e.g., "How is A connected to B?", "Find path between X and Y")
3. PAGERANK - For importance/influence queries (e.g., "Most important entities", "Key influencers")
4. FILTERED - For attribute-based queries (e.g., "Find all X with property Y", "Entities of type Z")
5. HYBRID - For complex queries requiring multiple strategies

Query: "{query}"

Respond with ONLY the strategy name (e.g., "MULTI_HOP"). No explanation needed."""

        messages = [LLMMessage(role="user", content=prompt)]

        # Call LLM
        if self.llm_client is None:
            # Fallback to rule-based classification if no LLM client
            return self._classify_with_rules(query)
        
        response = await self.llm_client.generate_text(
            messages=messages,
            temperature=0.0,  # Deterministic classification
            max_tokens=20,  # Short response
        )

        # Parse response
        strategy_str = response.content.strip().upper()

        # Map to enum
        strategy_mapping = {
            "VECTOR_SEARCH": RetrievalStrategy.VECTOR_SEARCH,
            "MULTI_HOP": RetrievalStrategy.MULTI_HOP,
            "PAGERANK": RetrievalStrategy.PAGERANK,
            "FILTERED": RetrievalStrategy.FILTERED,
            "HYBRID": RetrievalStrategy.HYBRID,
        }

        if strategy_str in strategy_mapping:
            return strategy_mapping[strategy_str]
        else:
            logger.warning(f"Unknown strategy from LLM: {strategy_str}, falling back to rule-based")
            return self._classify_with_rules(query)

    def _classify_with_rules(self, query: str) -> RetrievalStrategy:
        """
        Classify query using rule-based heuristics.

        Args:
            query: Query string

        Returns:
            RetrievalStrategy enum value
        """
        query_lower = query.lower()

        # Multi-hop patterns
        multi_hop_keywords = [
            "connected",
            "connection",
            "path",
            "relationship",
            "between",
            "link",
            "how is",
            "related to",
        ]
        if any(keyword in query_lower for keyword in multi_hop_keywords):
            return RetrievalStrategy.MULTI_HOP

        # Filtered patterns
        filtered_keywords = [
            "find all",
            "list all",
            "with property",
            "of type",
            "where",
            "filter",
        ]
        if any(keyword in query_lower for keyword in filtered_keywords):
            return RetrievalStrategy.FILTERED

        # PageRank patterns
        pagerank_keywords = [
            "most important",
            "key",
            "influential",
            "central",
            "top",
        ]
        if any(keyword in query_lower for keyword in pagerank_keywords):
            return RetrievalStrategy.PAGERANK

        # Default to vector search for semantic queries
        return RetrievalStrategy.VECTOR_SEARCH

    def clear_cache(self):
        """Clear the classification cache."""
        self._cache.clear()
        logger.debug("Classification cache cleared")

