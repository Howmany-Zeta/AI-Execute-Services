"""
Relation Deduplicator

Identifies and removes duplicate relations.
"""

from typing import List, Tuple, Dict
from aiecs.domain.knowledge_graph.models.relation import Relation


class RelationDeduplicator:
    """
    Deduplicate relations based on equivalence

    Two relations are considered duplicates if they have:
    - Same source entity
    - Same target entity
    - Same relation type
    - (Optionally) Similar properties

    This handles cases like:
    - Extracting "Alice WORKS_FOR Tech Corp" multiple times from different sentences
    - Multiple mentions of the same relationship with slight variations

    Example:
        ```python
        deduplicator = RelationDeduplicator()

        relations = [
            Relation(source="e1", target="e2", type="WORKS_FOR"),
            Relation(source="e1", target="e2", type="WORKS_FOR", properties={"since": "2020"}),
            Relation(source="e1", target="e3", type="KNOWS")
        ]

        deduplicated = await deduplicator.deduplicate(relations)
        # Returns: [
        #   Relation(source="e1", target="e2", type="WORKS_FOR", properties={"since": "2020"}),
        #   Relation(source="e1", target="e3", type="KNOWS")
        # ]
        ```
    """

    def __init__(self, merge_properties: bool = True):
        """
        Initialize relation deduplicator

        Args:
            merge_properties: If True, merge properties from duplicate relations
        """
        self.merge_properties = merge_properties

    async def deduplicate(self, relations: List[Relation]) -> List[Relation]:
        """
        Deduplicate a list of relations

        Args:
            relations: List of relations to deduplicate

        Returns:
            List of unique relations (with merged properties if enabled)
        """
        if not relations:
            return []

        # Group relations by (source, target, type) tuple
        relation_groups: Dict[Tuple[str, str, str], List[Relation]] = {}

        for relation in relations:
            key = (
                relation.source_id,
                relation.target_id,
                relation.relation_type,
            )

            if key not in relation_groups:
                relation_groups[key] = []
            relation_groups[key].append(relation)

        # For each group, merge duplicates
        deduplicated = []
        for key, group in relation_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                merged = self._merge_relations(group)
                deduplicated.append(merged)

        return deduplicated

    def _merge_relations(self, relations: List[Relation]) -> Relation:
        """
        Merge a group of duplicate relations into one

        Strategy:
        - Use first relation as base
        - Merge properties (prefer non-empty values)
        - Keep highest weight
        - Keep highest confidence

        Args:
            relations: List of duplicate relations

        Returns:
            Merged relation
        """
        if len(relations) == 1:
            return relations[0]

        # Use first relation as base
        base = relations[0]

        # Merge properties
        merged_properties = dict(base.properties) if base.properties else {}

        if self.merge_properties:
            for relation in relations[1:]:
                if relation.properties:
                    for key, value in relation.properties.items():
                        # Add property if not exists or current value is empty
                        if key not in merged_properties or not merged_properties[key]:
                            merged_properties[key] = value

        # Take highest weight
        max_weight = max(r.weight for r in relations)

        # Take highest confidence (if present in properties)
        confidences = [r.properties.get("_extraction_confidence", 0.5) for r in relations if r.properties]
        if confidences:
            merged_properties["_extraction_confidence"] = max(confidences)

        # Track merge count
        merged_properties["_merged_count"] = len(relations)

        # Create merged relation
        merged = Relation(
            id=base.id,
            relation_type=base.relation_type,
            source_id=base.source_id,
            target_id=base.target_id,
            properties=merged_properties,
            weight=max_weight,
            source=base.source,
        )

        return merged

    def find_duplicates(self, relations: List[Relation]) -> List[Tuple[Relation, Relation]]:
        """
        Find pairs of duplicate relations without merging

        Useful for debugging or manual review.

        Args:
            relations: List of relations to check

        Returns:
            List of (relation1, relation2) tuples that are duplicates
        """
        duplicates = []
        n = len(relations)

        for i in range(n):
            for j in range(i + 1, n):
                r1 = relations[i]
                r2 = relations[j]

                if self._are_duplicates(r1, r2):
                    duplicates.append((r1, r2))

        return duplicates

    def _are_duplicates(self, r1: Relation, r2: Relation) -> bool:
        """
        Check if two relations are duplicates

        Args:
            r1: First relation
            r2: Second relation

        Returns:
            True if relations are duplicates
        """
        return r1.source_id == r2.source_id and r1.target_id == r2.target_id and r1.relation_type == r2.relation_type
