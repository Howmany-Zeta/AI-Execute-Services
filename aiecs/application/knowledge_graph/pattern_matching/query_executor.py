"""
Custom Query Executor

Executes custom queries with pattern matching, projection, and aggregation.

Phase: 3.3 - Full Custom Query Execution
Version: 1.0
"""

from typing import List, Dict, Any, Optional
from aiecs.domain.knowledge_graph.models.query import GraphQuery
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.application.knowledge_graph.pattern_matching.pattern_matcher import (
    PatternMatcher,
    PatternMatch,
)


class CustomQueryExecutor:
    """
    Custom Query Executor

    Executes custom queries with:
    - Pattern matching
    - Result projection
    - Aggregation
    - Grouping
    """

    def __init__(self, graph_store: GraphStore):
        """
        Initialize custom query executor

        Args:
            graph_store: Graph storage backend
        """
        self.graph_store = graph_store
        self.pattern_matcher = PatternMatcher(graph_store)

    async def execute(self, query: GraphQuery, start_entity_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a custom query

        Args:
            query: Graph query with custom patterns
            start_entity_id: Optional starting entity ID

        Returns:
            Query results with matches, projections, and aggregations
        """
        # Execute pattern matching
        matches = await self._execute_pattern_matching(query, start_entity_id)

        # Apply projection if specified
        if query.projection:
            projected_results = self._apply_projection(matches, query.projection)
        else:
            projected_results = [self._match_to_dict(match) for match in matches]

        # Apply aggregation if specified
        if query.aggregations:
            aggregated_results = self._apply_aggregation(projected_results, query.aggregations, query.group_by)
            return {
                "matches": len(matches),
                "results": aggregated_results,
                "aggregated": True,
            }

        return {
            "matches": len(matches),
            "results": projected_results,
            "aggregated": False,
        }

    async def _execute_pattern_matching(self, query: GraphQuery, start_entity_id: Optional[str]) -> List[PatternMatch]:
        """
        Execute pattern matching based on query

        Args:
            query: Graph query
            start_entity_id: Optional starting entity ID

        Returns:
            List of pattern matches
        """
        max_matches = query.max_results or 100

        # Single pattern
        if query.pattern:
            return await self.pattern_matcher.match_pattern(query.pattern, start_entity_id, max_matches)

        # Multiple patterns (required)
        if query.patterns:
            if query.optional_patterns:
                # Required + optional patterns
                return await self.pattern_matcher.match_optional_patterns(
                    query.patterns,
                    query.optional_patterns,
                    start_entity_id,
                    max_matches,
                )
            else:
                # Only required patterns
                return await self.pattern_matcher.match_multiple_patterns(query.patterns, start_entity_id, max_matches)

        # No patterns specified
        return []

    def _match_to_dict(self, match: PatternMatch) -> Dict[str, Any]:
        """
        Convert pattern match to dictionary

        Args:
            match: Pattern match

        Returns:
            Dictionary representation
        """
        return {
            "entities": [
                {
                    "id": entity.id,
                    "type": entity.entity_type,
                    "properties": entity.properties,
                }
                for entity in match.entities
            ],
            "relations": [
                {
                    "id": relation.id,
                    "type": relation.relation_type,
                    "source": relation.source_id,
                    "target": relation.target_id,
                    "properties": relation.properties,
                }
                for relation in match.relations
            ],
            "score": match.score,
            "bindings": match.bindings,
        }

    def _apply_projection(self, matches: List[PatternMatch], projection: List[str]) -> List[Dict[str, Any]]:
        """
        Apply projection to matches

        Args:
            matches: Pattern matches
            projection: Fields to project

        Returns:
            Projected results
        """
        projected = []

        for match in matches:
            result = {}

            for field in projection:
                value = self._extract_field(match, field)
                result[field] = value

            projected.append(result)

        return projected

    def _extract_field(self, match: PatternMatch, field: str) -> Any:
        """
        Extract a field value from a match

        Supports dot notation for nested fields:
        - "id" -> first entity's ID
        - "entities[0].name" -> first entity's name
        - "entities[0].properties.age" -> first entity's age property

        Args:
            match: Pattern match
            field: Field path to extract

        Returns:
            Field value
        """
        # Handle simple fields
        if field == "score":
            return match.score

        if field == "entity_count":
            return len(match.entities)

        if field == "relation_count":
            return len(match.relations)

        # Handle entity fields
        if field.startswith("entities"):
            # Parse entities[0].name or entities[0].properties.age
            parts = field.split(".")

            # Extract index
            if "[" in parts[0]:
                index_str = parts[0].split("[")[1].split("]")[0]
                index = int(index_str)

                if index >= len(match.entities):
                    return None

                entity = match.entities[index]

                # Extract nested field
                if len(parts) == 1:
                    return {
                        "id": entity.id,
                        "type": entity.entity_type,
                        "properties": entity.properties,
                    }

                if parts[1] == "id":
                    return entity.id
                elif parts[1] == "type":
                    return entity.entity_type
                elif parts[1] == "properties" and len(parts) > 2:
                    return entity.properties.get(parts[2])
                elif parts[1] == "properties":
                    return entity.properties

        # Handle relation fields
        if field.startswith("relations"):
            parts = field.split(".")

            if "[" in parts[0]:
                index_str = parts[0].split("[")[1].split("]")[0]
                index = int(index_str)

                if index >= len(match.relations):
                    return None

                relation = match.relations[index]

                if len(parts) == 1:
                    return {
                        "id": relation.id,
                        "type": relation.relation_type,
                        "source": relation.source_id,
                        "target": relation.target_id,
                    }

                if parts[1] == "id":
                    return relation.id
                elif parts[1] == "type":
                    return relation.relation_type
                elif parts[1] == "source":
                    return relation.source_id
                elif parts[1] == "target":
                    return relation.target_id
                elif parts[1] == "properties" and len(parts) > 2:
                    return relation.properties.get(parts[2])

        # Handle bindings
        if field.startswith("bindings."):
            binding_name = field.split(".")[1]
            return match.bindings.get(binding_name)

        return None

    def _apply_aggregation(
        self,
        results: List[Dict[str, Any]],
        aggregations: Dict[str, str],
        group_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply aggregations to results

        Args:
            results: Projected results
            aggregations: Aggregation functions (e.g., {"count": "COUNT", "avg_age": "AVG(age)"})
            group_by: Optional fields to group by

        Returns:
            Aggregated results
        """
        if group_by:
            # Group results
            groups: Dict[Any, List[Dict[str, Any]]] = {}

            for result in results:
                # Create group key
                key_parts = []
                for field in group_by:
                    key_parts.append(str(result.get(field, "")))
                key = tuple(key_parts)

                if key not in groups:
                    groups[key] = []
                groups[key].append(result)

            # Aggregate each group
            aggregated = []

            for key, group_results in groups.items():
                agg_result = {}

                # Add group by fields
                for i, field in enumerate(group_by):
                    agg_result[field] = key[i]

                # Apply aggregations
                for agg_name, agg_func in aggregations.items():
                    agg_result[agg_name] = self._compute_aggregation(group_results, agg_func)

                aggregated.append(agg_result)

            return aggregated
        else:
            # Aggregate all results
            agg_result = {}

            for agg_name, agg_func in aggregations.items():
                agg_result[agg_name] = self._compute_aggregation(results, agg_func)

            return [agg_result]

    def _compute_aggregation(self, results: List[Dict[str, Any]], agg_func: str) -> Any:
        """
        Compute an aggregation function

        Supports:
        - COUNT: Count of results
        - SUM(field): Sum of field values
        - AVG(field): Average of field values
        - MIN(field): Minimum field value
        - MAX(field): Maximum field value

        Args:
            results: Results to aggregate
            agg_func: Aggregation function string

        Returns:
            Aggregated value
        """
        if agg_func == "COUNT":
            return len(results)

        # Parse function and field
        if "(" in agg_func:
            func_name = agg_func.split("(")[0]
            field = agg_func.split("(")[1].split(")")[0]

            # Extract field values
            values = []
            for result in results:
                value = result.get(field)
                if value is not None and isinstance(value, (int, float)):
                    values.append(value)

            if not values:
                return None

            if func_name == "SUM":
                return sum(values)
            elif func_name == "AVG":
                return sum(values) / len(values)
            elif func_name == "MIN":
                return min(values)
            elif func_name == "MAX":
                return max(values)

        return None
