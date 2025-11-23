"""
Search Context Management

This module tracks search history, learns user preferences, and provides
contextual suggestions for better search results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, cast


class SearchContext:
    """Manages search history and context for improved results"""

    def __init__(self, max_history: int = 10):
        """
        Initialize search context.

        Args:
            max_history: Maximum number of searches to keep in history
        """
        self.search_history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.topic_context: Optional[List[str]] = None
        self.user_preferences: Dict[str, Any] = {
            "preferred_domains": set(),
            "avoided_domains": set(),
            "preferred_content_types": [],
            "language": "en",
        }

    def add_search(
        self,
        query: str,
        results: List[Dict[str, Any]],
        user_feedback: Optional[Dict[str, Any]] = None,
    ):
        """
        Add search to history and update context.

        Args:
            query: Search query
            results: Search results
            user_feedback: Optional user feedback for learning
        """
        search_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "result_count": len(results),
            "clicked_results": [],
            "feedback": user_feedback,
        }

        self.search_history.append(search_record)

        # Maintain history size limit
        if len(self.search_history) > self.max_history:
            self.search_history.pop(0)

        # Update topic context
        self._update_topic_context(query, results)

        # Learn from feedback if provided
        if user_feedback:
            self._learn_preferences(results, user_feedback)

    def get_contextual_suggestions(self, current_query: str) -> Dict[str, Any]:
        """
        Generate context-aware suggestions for the current query.

        Args:
            current_query: Current search query

        Returns:
            Suggestions dictionary with related queries and parameters
        """
        suggestions: Dict[str, Any] = {
            "related_queries": [],
            "refinement_suggestions": [],
            "context_aware_params": {},
        }

        if not self.search_history:
            return suggestions

        # Find related historical queries
        related_queries = cast(List[Dict[str, Any]], suggestions["related_queries"])
        for record in reversed(self.search_history[-5:]):
            prev_query = record["query"]
            similarity = self._calculate_query_similarity(current_query, prev_query)

            if similarity > 0.5:
                related_queries.append(
                    {
                        "query": prev_query,
                        "similarity": similarity,
                        "timestamp": record["timestamp"],
                    }
                )

        # Suggest preferred sites if available
        preferred_domains = cast(Set[str], self.user_preferences["preferred_domains"])
        if preferred_domains:
            context_aware_params = cast(Dict[str, Any], suggestions["context_aware_params"])
            context_aware_params["preferred_sites"] = list(preferred_domains)

        return suggestions

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get search history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of search history records
        """
        if limit:
            return self.search_history[-limit:]
        return self.search_history.copy()

    def clear_history(self):
        """Clear search history"""
        self.search_history.clear()
        self.topic_context = None

    def get_preferences(self) -> Dict[str, Any]:
        """
        Get current user preferences.

        Returns:
            User preferences dictionary
        """
        preferred_domains = cast(Set[str], self.user_preferences["preferred_domains"])
        avoided_domains = cast(Set[str], self.user_preferences["avoided_domains"])
        preferred_content_types = cast(List[str], self.user_preferences["preferred_content_types"])
        return {
            "preferred_domains": list(preferred_domains),
            "avoided_domains": list(avoided_domains),
            "preferred_content_types": preferred_content_types.copy(),
            "language": self.user_preferences["language"],
        }

    def set_preference(self, key: str, value: Any):
        """
        Set a user preference.

        Args:
            key: Preference key
            value: Preference value
        """
        if key in self.user_preferences:
            pref_value = self.user_preferences[key]
            if isinstance(pref_value, set):
                if isinstance(value, (list, set)):
                    self.user_preferences[key] = set(value)
                else:
                    pref_set = cast(Set[str], pref_value)
                    pref_set.add(value)
            else:
                self.user_preferences[key] = value

    def _update_topic_context(self, query: str, results: List[Dict[str, Any]]):
        """
        Update topic context from query and results.

        Args:
            query: Search query
            results: Search results
        """
        # Simple implementation: extract common words
        words = query.lower().split()
        self.topic_context = words

    def _learn_preferences(self, results: List[Dict[str, Any]], feedback: Dict[str, Any]):
        """
        Learn user preferences from feedback.

        Args:
            results: Search results
            feedback: User feedback
        """
        # Learn from clicked/used results
        preferred_domains = cast(Set[str], self.user_preferences["preferred_domains"])
        if "clicked_indices" in feedback:
            for idx in feedback["clicked_indices"]:
                if 0 <= idx < len(results):
                    result = results[idx]
                    domain = result.get("displayLink", "")
                    if domain:
                        preferred_domains.add(domain)

        # Learn from disliked results
        avoided_domains = cast(Set[str], self.user_preferences["avoided_domains"])
        if "disliked_indices" in feedback:
            for idx in feedback["disliked_indices"]:
                if 0 <= idx < len(results):
                    result = results[idx]
                    domain = result.get("displayLink", "")
                    if domain:
                        avoided_domains.add(domain)

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate similarity between two queries using Jaccard index.

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score (0-1)
        """
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0
