"""
Evidence Synthesis

Combine and synthesize evidence from multiple sources for robust reasoning.
"""

import uuid
from typing import List, Optional, Dict, Any
from collections import defaultdict
from aiecs.domain.knowledge_graph.models.evidence import Evidence


class EvidenceSynthesizer:
    """
    Evidence Synthesizer

    Combines evidence from multiple sources to create more robust conclusions.

    Features:
    - Merge overlapping evidence
    - Calculate combined confidence
    - Detect contradictions
    - Synthesize explanations

    Example:
        ```python
        synthesizer = EvidenceSynthesizer()

        # Combine evidence from different sources
        combined = synthesizer.synthesize_evidence([ev1, ev2, ev3])

        # Get most reliable evidence
        reliable = synthesizer.filter_by_confidence(combined, threshold=0.7)
        ```
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        contradiction_threshold: float = 0.3,
    ):
        """
        Initialize evidence synthesizer

        Args:
            confidence_threshold: Minimum confidence for evidence
            contradiction_threshold: Threshold for detecting contradictions
        """
        self.confidence_threshold = confidence_threshold
        self.contradiction_threshold = contradiction_threshold

    def synthesize_evidence(self, evidence_list: List[Evidence], method: str = "weighted_average") -> List[Evidence]:
        """
        Synthesize evidence from multiple sources

        Args:
            evidence_list: List of evidence to synthesize
            method: Synthesis method ("weighted_average", "max", "voting")

        Returns:
            Synthesized evidence list
        """
        if not evidence_list:
            return []

        # Group evidence by entity overlap
        groups = self._group_overlapping_evidence(evidence_list)

        # Synthesize each group
        synthesized = []
        for group in groups:
            if len(group) == 1:
                synthesized.append(group[0])
            else:
                combined = self._combine_evidence_group(group, method)
                synthesized.append(combined)

        return synthesized

    def _group_overlapping_evidence(self, evidence_list: List[Evidence]) -> List[List[Evidence]]:
        """
        Group evidence that refers to overlapping entities

        Args:
            evidence_list: List of evidence to group

        Returns:
            List of evidence groups
        """
        groups = []
        used = set()

        for i, ev1 in enumerate(evidence_list):
            if i in used:
                continue

            group = [ev1]
            ev1_entities = set(ev1.get_entity_ids())
            used.add(i)

            # Find overlapping evidence
            for j, ev2 in enumerate(evidence_list):
                if j <= i or j in used:
                    continue

                ev2_entities = set(ev2.get_entity_ids())
                overlap = ev1_entities & ev2_entities

                # If significant overlap, add to group
                if len(overlap) > 0:
                    group.append(ev2)
                    used.add(j)

            groups.append(group)

        return groups

    def _combine_evidence_group(self, group: List[Evidence], method: str) -> Evidence:
        """
        Combine a group of overlapping evidence

        Args:
            group: Group of evidence to combine
            method: Combination method

        Returns:
            Combined evidence
        """
        if not group:
            raise ValueError("Cannot combine empty evidence group")

        if len(group) == 1:
            return group[0]

        # Collect all entities and relations
        all_entities = []
        all_relations = []
        all_paths = []
        seen_entity_ids = set()
        seen_relation_ids = set()

        for ev in group:
            for entity in ev.entities:
                if entity.id not in seen_entity_ids:
                    all_entities.append(entity)
                    seen_entity_ids.add(entity.id)

            for relation in ev.relations:
                if relation.id not in seen_relation_ids:
                    all_relations.append(relation)
                    seen_relation_ids.add(relation.id)

            all_paths.extend(ev.paths)

        # Calculate combined confidence and relevance
        if method == "weighted_average":
            # Weight by number of supporting evidence
            total_confidence = sum(ev.confidence for ev in group)
            total_relevance = sum(ev.relevance_score for ev in group)
            confidence = total_confidence / len(group)
            relevance = total_relevance / len(group)

        elif method == "max":
            # Take maximum
            confidence = max(ev.confidence for ev in group)
            relevance = max(ev.relevance_score for ev in group)

        elif method == "voting":
            # Majority voting with confidence weights
            confidence = sum(ev.confidence for ev in group) / len(group)
            relevance = sum(ev.relevance_score for ev in group) / len(group)

        else:
            # Default to weighted average
            confidence = sum(ev.confidence for ev in group) / len(group)
            relevance = sum(ev.relevance_score for ev in group) / len(group)

        # Boost confidence if multiple sources agree
        agreement_boost = min(0.1 * (len(group) - 1), 0.3)
        confidence = min(1.0, confidence + agreement_boost)

        # Create combined explanation
        sources = list(set(ev.source for ev in group if ev.source))
        explanation = f"Combined from {len(group)} sources: {', '.join(sources[:3])}"
        if len(group) > 1:
            explanation += f"\nAgreement across {len(group)} pieces of evidence increases confidence"

        # Create synthesized evidence
        combined = Evidence(
            evidence_id=f"synth_{uuid.uuid4().hex[:8]}",
            evidence_type=group[0].evidence_type,
            entities=all_entities,
            relations=all_relations,
            paths=all_paths,
            confidence=confidence,
            relevance_score=relevance,
            explanation=explanation,
            source="synthesis",
            metadata={
                "source_count": len(group),
                "source_evidence_ids": [ev.evidence_id for ev in group],
                "synthesis_method": method,
            },
        )

        return combined

    def filter_by_confidence(self, evidence_list: List[Evidence], threshold: Optional[float] = None) -> List[Evidence]:
        """
        Filter evidence by confidence threshold

        Args:
            evidence_list: List of evidence to filter
            threshold: Confidence threshold (uses default if None)

        Returns:
            Filtered evidence list
        """
        threshold = threshold if threshold is not None else self.confidence_threshold
        return [ev for ev in evidence_list if ev.confidence >= threshold]

    def detect_contradictions(self, evidence_list: List[Evidence]) -> List[Dict[str, Any]]:
        """
        Detect contradictions in evidence

        Args:
            evidence_list: List of evidence to check

        Returns:
            List of detected contradictions
        """
        contradictions = []

        # Group by entity
        entity_evidence: Dict[str, List[Evidence]] = defaultdict(list)
        for ev in evidence_list:
            for entity in ev.entities:
                entity_evidence[entity.id].append(ev)

        # Check for contradictory claims
        for entity_id, evidence_group in entity_evidence.items():
            if len(evidence_group) < 2:
                continue

            # Look for low confidence with high relevance (potential
            # contradiction)
            confidences = [ev.confidence for ev in evidence_group]
            if max(confidences) - min(confidences) > self.contradiction_threshold:
                contradictions.append(
                    {
                        "entity_id": entity_id,
                        "evidence_ids": [ev.evidence_id for ev in evidence_group],
                        "confidence_range": (
                            min(confidences),
                            max(confidences),
                        ),
                        "description": f"Conflicting confidence scores for entity {entity_id}",
                    }
                )

        return contradictions

    def estimate_overall_confidence(self, evidence_list: List[Evidence]) -> float:
        """
        Estimate overall confidence from evidence list

        Considers:
        - Individual confidence scores
        - Agreement across evidence
        - Source diversity

        Args:
            evidence_list: List of evidence

        Returns:
            Overall confidence score (0-1)
        """
        if not evidence_list:
            return 0.0

        # Base confidence (average)
        base_confidence = sum(ev.confidence for ev in evidence_list) / len(evidence_list)

        # Source diversity bonus
        sources = set(ev.source for ev in evidence_list if ev.source)
        diversity_bonus = min(0.1 * (len(sources) - 1), 0.2)

        # Agreement bonus (entities appearing in multiple evidence)
        entity_counts: Dict[str, int] = defaultdict(int)
        for ev in evidence_list:
            for entity_id in ev.get_entity_ids():
                entity_counts[entity_id] += 1

        # Average entity appearance count
        if entity_counts:
            avg_appearances = sum(entity_counts.values()) / len(entity_counts)
            agreement_bonus = min(0.1 * (avg_appearances - 1), 0.15)
        else:
            agreement_bonus = 0.0

        # Combined confidence
        overall = base_confidence + diversity_bonus + agreement_bonus
        return min(1.0, overall)

    def rank_by_reliability(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """
        Rank evidence by reliability

        Considers:
        - Confidence score
        - Relevance score
        - Source credibility

        Args:
            evidence_list: List of evidence to rank

        Returns:
            Ranked evidence list (most reliable first)
        """
        # Calculate reliability score for each evidence
        scored = []
        for ev in evidence_list:
            # Base score from confidence and relevance
            reliability = (ev.confidence * 0.6) + (ev.relevance_score * 0.4)

            # Boost for synthesis (already vetted)
            if ev.source == "synthesis":
                reliability *= 1.1

            # Boost for multiple supporting elements
            element_count = len(ev.entities) + len(ev.relations) + len(ev.paths)
            if element_count > 3:
                reliability *= 1.05

            reliability = min(1.0, reliability)
            scored.append((ev, reliability))

        # Sort by reliability (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        return [ev for ev, score in scored]
