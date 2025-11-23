"""
Inference Engine

Rule-based logical inference over knowledge graphs.
"""

import uuid
import time
from typing import List, Optional, Dict, Any, Set, Tuple
from collections import defaultdict
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.inference_rule import (
    InferenceRule,
    InferenceStep,
    InferenceResult,
    RuleType,
)
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType


class InferenceCache:
    """
    Cache for inference results

    Stores previously computed inference results to avoid recomputation.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[float] = None):
        """
        Initialize inference cache

        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[InferenceResult, float]] = {}
        self._access_times: Dict[str, float] = {}

    def _make_key(
        self,
        relation_type: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> str:
        """Create cache key"""
        if source_id and target_id:
            return f"{relation_type}:{source_id}:{target_id}"
        elif source_id:
            return f"{relation_type}:{source_id}:*"
        elif target_id:
            return f"{relation_type}:*:{target_id}"
        else:
            return f"{relation_type}:*:*"

    def get(
        self,
        relation_type: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> Optional[InferenceResult]:
        """
        Get cached inference result

        Args:
            relation_type: Relation type
            source_id: Source entity ID
            target_id: Target entity ID

        Returns:
            Cached result or None
        """
        key = self._make_key(relation_type, source_id, target_id)

        if key not in self._cache:
            return None

        result, cached_time = self._cache[key]

        # Check TTL
        if self.ttl_seconds and (time.time() - cached_time) > self.ttl_seconds:
            del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
            return None

        # Update access time
        self._access_times[key] = time.time()
        return result

    def put(
        self,
        relation_type: str,
        result: InferenceResult,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> None:
        """
        Cache inference result

        Args:
            relation_type: Relation type
            result: Inference result to cache
            source_id: Source entity ID
            target_id: Target entity ID
        """
        key = self._make_key(relation_type, source_id, target_id)

        # Evict if cache is full (LRU)
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove least recently used
            lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
            del self._cache[lru_key]
            del self._access_times[lru_key]

        self._cache[key] = (result, time.time())
        self._access_times[key] = time.time()

    def clear(self) -> None:
        """Clear all cached results"""
        self._cache.clear()
        self._access_times.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }


class InferenceEngine:
    """
    Rule-Based Inference Engine

    Applies logical inference rules to infer new relations from existing ones.

    Features:
    - Transitive inference (A->B, B->C => A->C)
    - Symmetric inference (A->B => B->A)
    - Custom inference rules
    - Result caching
    - Explainability (trace inference steps)

    Example:
        ```python
        engine = InferenceEngine(graph_store)

        # Add rules
        engine.add_rule(InferenceRule(
            rule_id="transitive_works_for",
            rule_type=RuleType.TRANSITIVE,
            relation_type="WORKS_FOR"
        ))

        # Infer relations
        result = await engine.infer_relations(
            relation_type="WORKS_FOR",
            max_steps=3
        )

        print(f"Inferred {len(result.inferred_relations)} relations")
        print(result.get_explanation_string())
        ```
    """

    def __init__(self, graph_store: GraphStore, cache: Optional[InferenceCache] = None):
        """
        Initialize inference engine

        Args:
            graph_store: Graph storage backend
            cache: Optional inference cache (creates one if not provided)
        """
        self.graph_store = graph_store
        self.cache = cache or InferenceCache()
        self.rules: Dict[str, InferenceRule] = {}
        self.relation_type_schemas: Dict[str, RelationType] = {}

    def add_rule(self, rule: InferenceRule) -> None:
        """
        Add an inference rule

        Args:
            rule: Inference rule to add
        """
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        """
        Remove an inference rule

        Args:
            rule_id: ID of rule to remove
        """
        if rule_id in self.rules:
            del self.rules[rule_id]

    def get_rules(self, relation_type: Optional[str] = None) -> List[InferenceRule]:
        """
        Get inference rules

        Args:
            relation_type: Filter by relation type (None = all)

        Returns:
            List of inference rules
        """
        rules = list(self.rules.values())
        if relation_type:
            rules = [r for r in rules if r.relation_type == relation_type]
        return rules

    async def infer_relations(
        self,
        relation_type: str,
        max_steps: int = 10,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> InferenceResult:
        """
        Infer relations using enabled rules

        Args:
            relation_type: Relation type to infer
            max_steps: Maximum number of inference steps
            source_id: Optional source entity ID filter
            target_id: Optional target entity ID filter
            use_cache: Whether to use cache

        Returns:
            Inference result with inferred relations and steps
        """
        # Check cache
        if use_cache:
            cached = self.cache.get(relation_type, source_id, target_id)
            if cached:
                return cached

        time.time()
        inferred_relations: List[Relation] = []
        inference_steps: List[InferenceStep] = []
        # Track inferred relation IDs to avoid duplicates
        visited: Set[str] = set()

        # Get applicable rules
        applicable_rules = [rule for rule in self.get_rules(relation_type) if rule.enabled]

        if not applicable_rules:
            result = InferenceResult(
                inferred_relations=[],
                inference_steps=[],
                total_steps=0,
                confidence=0.0,
                explanation=f"No inference rules enabled for relation type: {relation_type}",
            )
            return result

        # Get existing relations by traversing the graph
        # We'll collect relations as we discover them through inference
        # Start with relations we can find through get_neighbors
        existing_relations: List[Relation] = []

        # For inference, we'll discover relations as we traverse
        # This is a limitation of the current GraphStore interface
        # In practice, we'd query for all relations of a type directly

        # Apply rules iteratively
        current_relations = existing_relations.copy()
        step_count = 0

        while step_count < max_steps:
            new_relations = []

            for rule in applicable_rules:
                if rule.rule_type == RuleType.TRANSITIVE:
                    inferred = await self._apply_transitive_rule(rule, current_relations, visited)
                    new_relations.extend(inferred)
                elif rule.rule_type == RuleType.SYMMETRIC:
                    inferred = await self._apply_symmetric_rule(rule, current_relations, visited)
                    new_relations.extend(inferred)

            if not new_relations:
                break  # No new relations inferred

            # Add new relations
            for rel, step in new_relations:
                if rel.id not in visited:
                    inferred_relations.append(rel)
                    inference_steps.append(step)
                    visited.add(rel.id)
                    current_relations.append(rel)

            step_count += 1

        # Calculate overall confidence
        if inference_steps:
            confidence = sum(step.confidence for step in inference_steps) / len(inference_steps)
        else:
            confidence = 0.0

        # Create result
        result = InferenceResult(
            inferred_relations=inferred_relations,
            inference_steps=inference_steps,
            total_steps=step_count,
            confidence=confidence,
            explanation=f"Inferred {len(inferred_relations)} relations using {len(applicable_rules)} rules in {step_count} steps",
        )

        # Cache result
        if use_cache:
            self.cache.put(relation_type, result, source_id, target_id)

        return result

    async def _get_relations(self, relation_type: str) -> List[Relation]:
        """
        Get all relations of a given type

        Note: This is a simplified implementation that uses traversal.
        In production, GraphStore should have a get_relations_by_type method.
        """
        relations: List[Relation] = []
        # visited_entities: Set[str] = set()  # Reserved for future use

        # Get all entities (we'll need to traverse to find them)
        # For now, we'll collect relations as we traverse
        # This is inefficient but works for the current interface

        # Try to get relations from paths
        # We'll use a simple approach: traverse from a few entities
        # In practice, this should be optimized in GraphStore

        return relations

    async def _apply_transitive_rule(self, rule: InferenceRule, relations: List[Relation], visited: Set[str]) -> List[Tuple[Relation, InferenceStep]]:
        """
        Apply transitive rule: A->B, B->C => A->C

        Args:
            rule: Transitive rule to apply
            relations: Existing relations
            visited: Set of already inferred relation IDs

        Returns:
            List of (inferred_relation, inference_step) tuples
        """
        inferred = []

        # Build index: source -> target
        source_to_targets: Dict[str, List[Relation]] = defaultdict(list)
        for rel in relations:
            if rel.relation_type == rule.relation_type:
                source_to_targets[rel.source_id].append(rel)

        # Find transitive chains
        for rel1 in relations:
            if rel1.relation_type != rule.relation_type:
                continue

            # rel1: A -> B
            # Find relations where B is source: B -> C
            for rel2 in source_to_targets.get(rel1.target_id, []):
                # Check if A -> C already exists
                inferred_id = f"inf_{rel1.source_id}_{rel2.target_id}_{rule.relation_type}"

                if inferred_id in visited:
                    continue

                # Check if relation already exists
                existing = await self.graph_store.get_relation(inferred_id)
                if existing:
                    continue

                # Create inferred relation
                # Confidence decays with each step
                confidence = min(rel1.weight, rel2.weight) * (1.0 - rule.confidence_decay)

                inferred_rel = Relation(
                    id=inferred_id,
                    relation_type=rule.relation_type,
                    source_id=rel1.source_id,
                    target_id=rel2.target_id,
                    weight=confidence,
                    properties={
                        "inferred": True,
                        "source_relations": [rel1.id, rel2.id],
                        "rule_id": rule.rule_id,
                    },
                )

                # Create inference step
                step = InferenceStep(
                    step_id=f"step_{uuid.uuid4().hex[:8]}",
                    inferred_relation=inferred_rel,
                    source_relations=[rel1, rel2],
                    rule=rule,
                    confidence=confidence,
                    explanation=f"Transitive: {rel1.source_id} -> {rel1.target_id} -> {rel2.target_id} => {rel1.source_id} -> {rel2.target_id}",
                )

                inferred.append((inferred_rel, step))

        return inferred

    async def _apply_symmetric_rule(self, rule: InferenceRule, relations: List[Relation], visited: Set[str]) -> List[Tuple[Relation, InferenceStep]]:
        """
        Apply symmetric rule: A->B => B->A

        Args:
            rule: Symmetric rule to apply
            relations: Existing relations
            visited: Set of already inferred relation IDs

        Returns:
            List of (inferred_relation, inference_step) tuples
        """
        inferred = []

        # Build set of existing relations (source, target) pairs
        existing_pairs = set()
        for rel in relations:
            if rel.relation_type == rule.relation_type:
                existing_pairs.add((rel.source_id, rel.target_id))

        # Find relations that need symmetric inference
        for rel in relations:
            if rel.relation_type != rule.relation_type:
                continue

            # Check if reverse already exists
            reverse_pair = (rel.target_id, rel.source_id)
            if reverse_pair in existing_pairs:
                continue

            # Check if already inferred
            inferred_id = f"inf_{rel.target_id}_{rel.source_id}_{rule.relation_type}"
            if inferred_id in visited:
                continue

            # Check if relation already exists
            existing = await self.graph_store.get_relation(inferred_id)
            if existing:
                continue

            # Create inferred relation
            # Confidence slightly lower than original
            confidence = rel.weight * (1.0 - rule.confidence_decay)

            inferred_rel = Relation(
                id=inferred_id,
                relation_type=rule.relation_type,
                source_id=rel.target_id,
                target_id=rel.source_id,
                weight=confidence,
                properties={
                    "inferred": True,
                    "source_relations": [rel.id],
                    "rule_id": rule.rule_id,
                },
            )

            # Create inference step
            step = InferenceStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                inferred_relation=inferred_rel,
                source_relations=[rel],
                rule=rule,
                confidence=confidence,
                explanation=f"Symmetric: {rel.source_id} -> {rel.target_id} => {rel.target_id} -> {rel.source_id}",
            )

            inferred.append((inferred_rel, step))

        return inferred

    def get_inference_trace(self, result: InferenceResult) -> List[str]:
        """
        Get human-readable trace of inference steps

        Args:
            result: Inference result

        Returns:
            List of trace strings
        """
        trace = []
        trace.append(f"Inference trace for {result.total_steps} steps:")

        for i, step in enumerate(result.inference_steps, 1):
            trace.append(f"  Step {i}: {step.explanation}")
            trace.append(f"    Confidence: {step.confidence:.2f}")
            trace.append(f"    Rule: {step.rule.rule_id} ({step.rule.rule_type})")

        return trace
