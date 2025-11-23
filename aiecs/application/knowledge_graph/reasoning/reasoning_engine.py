"""
Reasoning Engine

Multi-hop reasoning over knowledge graphs with evidence collection and answer generation.
"""

import uuid
import time
from typing import List, Optional, Dict, Any, Tuple
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.evidence import (
    Evidence,
    EvidenceType,
    ReasoningResult,
)
from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan, QueryStep
from aiecs.domain.knowledge_graph.models.query import QueryType
from aiecs.application.knowledge_graph.traversal.enhanced_traversal import (
    EnhancedTraversal,
)
from aiecs.application.knowledge_graph.traversal.path_scorer import PathScorer
from aiecs.application.knowledge_graph.reasoning.query_planner import (
    QueryPlanner,
)


class ReasoningEngine:
    """
    Multi-Hop Reasoning Engine

    Executes query plans, collects evidence, and generates answers
    for complex multi-hop queries over knowledge graphs.

    Features:
    - Execute query plans from QueryPlanner
    - Multi-hop path finding
    - Evidence collection and scoring
    - Path ranking by relevance
    - Answer generation from evidence

    Example:
        ```python
        engine = ReasoningEngine(graph_store)

        # Reason over a query
        result = await engine.reason(
            query="What companies does Alice know people at?",
            context={"start_entity_id": "person_alice"}
        )

        print(f"Answer: {result.answer}")
        print(f"Confidence: {result.confidence}")
        print(f"Evidence: {result.evidence_count} pieces")
        ```
    """

    def __init__(
        self,
        graph_store: GraphStore,
        query_planner: Optional[QueryPlanner] = None,
    ):
        """
        Initialize reasoning engine

        Args:
            graph_store: Graph storage backend
            query_planner: Query planner (creates one if not provided)
        """
        self.graph_store = graph_store
        self.query_planner = query_planner or QueryPlanner(graph_store)
        self.traversal = EnhancedTraversal(graph_store)
        self.path_scorer = PathScorer()

    async def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        max_hops: int = 3,
        max_evidence: int = 20,
    ) -> ReasoningResult:
        """
        Perform multi-hop reasoning on a query

        Args:
            query: Natural language query
            context: Query context (entity IDs, embeddings, etc.)
            max_hops: Maximum number of hops for traversal
            max_evidence: Maximum number of evidence pieces to collect

        Returns:
            Reasoning result with evidence and answer
        """
        start_time = time.time()
        context = context or {}
        trace = []

        # Step 1: Plan the query
        trace.append(f"Planning query: {query}")
        plan = self.query_planner.plan_query(query, context)
        trace.append(f"Created plan with {len(plan.steps)} steps")

        # Step 2: Execute plan and collect evidence
        trace.append("Executing query plan...")
        evidence = await self._execute_plan_with_evidence(plan, trace)

        # Fallback: If no evidence found but start_entity_id is provided, try
        # direct traversal
        if not evidence and context.get("start_entity_id"):
            import logging

            logger = logging.getLogger(__name__)

            trace.append(f"WARNING: Query plan returned no evidence. Plan had {len(plan.steps)} steps.")
            trace.append(f"Plan steps: {[s.step_id + ':' + s.operation.value for s in plan.steps]}")
            logger.warning(f"Query plan returned no evidence. " f"Plan ID: {plan.plan_id}, Steps: {len(plan.steps)}, " f"Query: {query}, Context: {context}")

            trace.append(f"FALLBACK: Trying direct traversal from {context['start_entity_id']}")
            start_id = context["start_entity_id"]
            target_id = context.get("target_entity_id")

            try:
                paths = await self.find_multi_hop_paths(
                    start_entity_id=start_id,
                    target_entity_id=target_id,
                    max_hops=max_hops,
                    relation_types=context.get("relation_types"),
                    max_paths=max_evidence,
                )

                if paths:
                    path_evidence = await self.collect_evidence_from_paths(paths, source="direct_traversal_fallback")
                    evidence.extend(path_evidence)
                    trace.append(f"FALLBACK SUCCESS: Found {len(path_evidence)} evidence pieces from direct traversal")
                    logger.info(f"Fallback traversal succeeded: {len(path_evidence)} evidence pieces from {start_id}")
                else:
                    trace.append(f"FALLBACK FAILED: No paths found from {start_id}")
                    logger.warning(f"Fallback traversal found no paths from {start_id}")
            except Exception as e:
                trace.append(f"FALLBACK ERROR: {str(e)}")
                logger.error(f"Fallback traversal failed: {str(e)}", exc_info=True)

        # Step 3: Rank and filter evidence
        trace.append(f"Collected {len(evidence)} pieces of evidence")
        evidence = self._rank_and_filter_evidence(evidence, max_evidence)
        trace.append(f"Filtered to top {len(evidence)} pieces")

        # Step 4: Generate answer
        trace.append("Generating answer from evidence...")
        answer, confidence = self._generate_answer(query, evidence)

        execution_time = (time.time() - start_time) * 1000

        return ReasoningResult(
            query=query,
            evidence=evidence,
            answer=answer,
            confidence=confidence,
            reasoning_trace=trace,
            execution_time_ms=execution_time,
            metadata={"plan_id": plan.plan_id, "num_steps": len(plan.steps)},
        )

    async def find_multi_hop_paths(
        self,
        start_entity_id: str,
        target_entity_id: Optional[str] = None,
        max_hops: int = 3,
        relation_types: Optional[List[str]] = None,
        max_paths: int = 10,
    ) -> List[Path]:
        """
        Find multi-hop paths between entities

        Args:
            start_entity_id: Starting entity ID
            target_entity_id: Target entity ID (None for all reachable)
            max_hops: Maximum number of hops
            relation_types: Allowed relation types (None for all)
            max_paths: Maximum number of paths to return

        Returns:
            List of paths found
        """
        # Use graph store's traverse method
        paths = await self.graph_store.traverse(
            start_entity_id=start_entity_id,
            relation_type=None,  # Will filter later if needed
            max_depth=max_hops,
            max_results=max_paths * 2,  # Get more, then filter
        )

        # Filter by target if specified
        if target_entity_id:
            paths = [path for path in paths if path.nodes[-1].id == target_entity_id]

        # Filter by relation types if specified
        if relation_types:
            paths = [path for path in paths if all(rel.relation_type in relation_types for rel in path.edges)]

        return paths[:max_paths]

    async def collect_evidence_from_paths(self, paths: List[Path], source: str = "path_finding") -> List[Evidence]:
        """
        Collect evidence from paths

        Args:
            paths: List of paths to extract evidence from
            source: Source identifier for the evidence

        Returns:
            List of evidence pieces
        """
        evidence_list = []

        for i, path in enumerate(paths):
            # Calculate confidence based on path properties
            confidence = self._calculate_path_confidence(path)

            # Calculate relevance (for now, use path length as proxy)
            relevance = 1.0 / max(1, len(path.nodes) - 1)

            # Create explanation
            explanation = self._create_path_explanation(path)

            evidence = Evidence(
                evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                evidence_type=EvidenceType.PATH,
                entities=path.nodes,
                relations=path.edges,
                paths=[path],
                confidence=confidence,
                relevance_score=relevance,
                explanation=explanation,
                source=source,
                metadata={"path_index": i, "path_length": len(path.nodes)},
            )

            evidence_list.append(evidence)

        return evidence_list

    def rank_evidence(self, evidence: List[Evidence], ranking_method: str = "combined_score") -> List[Evidence]:
        """
        Rank evidence by relevance

        Args:
            evidence: List of evidence to rank
            ranking_method: Method to use for ranking
                - "combined_score": confidence * relevance
                - "confidence": confidence only
                - "relevance": relevance only

        Returns:
            Ranked evidence list
        """
        if ranking_method == "combined_score":
            return sorted(evidence, key=lambda e: e.combined_score, reverse=True)
        elif ranking_method == "confidence":
            return sorted(evidence, key=lambda e: e.confidence, reverse=True)
        elif ranking_method == "relevance":
            return sorted(evidence, key=lambda e: e.relevance_score, reverse=True)
        else:
            return evidence

    def _calculate_path_confidence(self, path: Path) -> float:
        """Calculate confidence score for a path"""
        if not path.edges:
            return 1.0

        # Use average weight of relations as confidence proxy
        weights = [rel.weight for rel in path.edges if rel.weight is not None]
        if not weights:
            return 0.5

        return sum(weights) / len(weights)

    def _create_path_explanation(self, path: Path) -> str:
        """Create human-readable explanation of a path"""
        if len(path.nodes) == 1:
            entity = path.nodes[0]
            return f"Entity: {entity.properties.get('name', entity.id)} ({entity.entity_type})"

        parts = []
        for i, entity in enumerate(path.nodes):
            entity_name = entity.properties.get("name", entity.id)
            entity_type = entity.entity_type
            parts.append(f"{entity_name} ({entity_type})")

            if i < len(path.edges):
                relation = path.edges[i]
                parts.append(f" --[{relation.relation_type}]--> ")

        return "".join(parts)

    async def _execute_plan_with_evidence(self, plan: QueryPlan, trace: List[str]) -> List[Evidence]:
        """Execute query plan and collect evidence"""
        import logging

        logger = logging.getLogger(__name__)

        all_evidence = []
        completed_steps = set()
        step_results: Dict[str, Any] = {}

        # Get execution order
        execution_order = plan.get_execution_order()
        trace.append(f"Plan has {len(plan.steps)} steps, execution order: {execution_order}")

        for level, step_ids in enumerate(execution_order):
            trace.append(f"Executing level {level}: {step_ids}")

            # Execute steps in this level (could be parallelized)
            for step_id in step_ids:
                try:
                    step = next(s for s in plan.steps if s.step_id == step_id)
                    trace.append(f"  Executing {step_id}: {step.operation.value} - {step.description}")

                    # Execute step
                    step_evidence = await self._execute_step(step, step_results)
                    all_evidence.extend(step_evidence)

                    # Store results for dependent steps
                    step_results[step_id] = step_evidence
                    completed_steps.add(step_id)

                    trace.append(f"  {step_id}: Collected {len(step_evidence)} evidence")
                    logger.debug(f"Step {step_id} completed: {len(step_evidence)} evidence pieces")

                    if len(step_evidence) == 0:
                        trace.append(f"  WARNING: {step_id} returned no evidence")
                        logger.warning(
                            f"Step {step_id} ({step.operation.value}) returned no evidence. "
                            f"Query: {step.query.query_type}, "
                            f"Entity ID: {getattr(step.query, 'entity_id', None)}, "
                            f"Source: {getattr(step.query, 'source_entity_id', None)}"
                        )
                except Exception as e:
                    error_msg = f"Error executing step {step_id}: {str(e)}"
                    trace.append(f"  ERROR: {error_msg}")
                    logger.error(error_msg, exc_info=True)
                    # Continue with other steps even if one fails

        return all_evidence

    async def _execute_step(self, step: QueryStep, previous_results: Dict[str, Any]) -> List[Evidence]:
        """Execute a single query step"""
        query = step.query
        evidence = []

        # Entity lookup
        if query.query_type == QueryType.ENTITY_LOOKUP:
            if query.entity_id:
                entity = await self.graph_store.get_entity(query.entity_id)
                if entity:
                    evidence.append(
                        Evidence(
                            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                            evidence_type=EvidenceType.ENTITY,
                            entities=[entity],
                            confidence=1.0,
                            relevance_score=1.0,
                            explanation=f"Found entity: {entity.id}",
                            source=step.step_id,
                        )
                    )

        # Vector search
        elif query.query_type == QueryType.VECTOR_SEARCH:
            if query.embedding:
                results = await self.graph_store.vector_search(
                    query_embedding=query.embedding,
                    entity_type=query.entity_type,
                    max_results=query.max_results,
                    score_threshold=query.score_threshold,
                )

                for entity, score in results:
                    evidence.append(
                        Evidence(
                            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                            evidence_type=EvidenceType.ENTITY,
                            entities=[entity],
                            confidence=score,
                            relevance_score=score,
                            explanation=f"Similar entity: {entity.id} (score: {score:.2f})",
                            source=step.step_id,
                        )
                    )

        # Traversal
        elif query.query_type == QueryType.TRAVERSAL:
            import logging

            logger = logging.getLogger(__name__)

            # Get starting entities from previous steps or query
            start_ids = []
            if query.entity_id:
                start_ids = [query.entity_id]
                logger.debug(f"TRAVERSAL: Using entity_id from query: {query.entity_id}")
            elif step.depends_on:
                # Get entities from dependent steps
                for dep_id in step.depends_on:
                    if dep_id in previous_results:
                        dep_evidence = previous_results[dep_id]
                        extracted_ids = [e.id for ev in dep_evidence for e in ev.entities]
                        start_ids.extend(extracted_ids)
                        logger.debug(f"TRAVERSAL: Extracted {len(extracted_ids)} entity IDs from step {dep_id}")
                    else:
                        logger.warning(f"TRAVERSAL: Dependent step {dep_id} not found in previous_results")
            else:
                logger.warning("TRAVERSAL: No entity_id and no dependencies. Cannot traverse.")

            if not start_ids:
                logger.warning(
                    f"TRAVERSAL step {step.step_id} has no starting entities. "
                    f"Query entity_id: {getattr(query, 'entity_id', None)}, "
                    f"Dependencies: {step.depends_on}, "
                    f"Previous results keys: {list(previous_results.keys())}"
                )
            else:
                # Traverse from each starting entity
                # Limit starting points
                for start_id in start_ids[: query.max_results]:
                    try:
                        paths = await self.graph_store.traverse(
                            start_entity_id=start_id,
                            relation_type=query.relation_type,
                            max_depth=query.max_depth,
                            max_results=query.max_results,
                        )
                        logger.debug(f"TRAVERSAL: Found {len(paths)} paths from {start_id}")

                        # Convert paths to evidence
                        path_evidence = await self.collect_evidence_from_paths(paths, source=step.step_id)
                        evidence.extend(path_evidence)
                        logger.debug(f"TRAVERSAL: Collected {len(path_evidence)} evidence from {start_id}")
                    except Exception as e:
                        logger.error(
                            f"TRAVERSAL: Error traversing from {start_id}: {str(e)}",
                            exc_info=True,
                        )

        # Path finding
        elif query.query_type == QueryType.PATH_FINDING:
            if query.source_entity_id and query.target_entity_id:
                paths = await self.find_multi_hop_paths(
                    start_entity_id=query.source_entity_id,
                    target_entity_id=query.target_entity_id,
                    max_hops=query.max_depth,
                    max_paths=query.max_results,
                )

                path_evidence = await self.collect_evidence_from_paths(paths, source=step.step_id)
                evidence.extend(path_evidence)

        return evidence

    def _rank_and_filter_evidence(self, evidence: List[Evidence], max_evidence: int) -> List[Evidence]:
        """Rank and filter evidence to top N"""
        # Rank by combined score
        ranked = self.rank_evidence(evidence, ranking_method="combined_score")

        # Filter to top N
        return ranked[:max_evidence]

    def _generate_answer(self, query: str, evidence: List[Evidence]) -> Tuple[str, float]:
        """
        Generate answer from evidence

        Args:
            query: Original query
            evidence: Collected evidence

        Returns:
            (answer, confidence) tuple
        """
        if not evidence:
            return "No evidence found to answer the query.", 0.0

        # Calculate overall confidence
        if evidence:
            confidence = sum(e.combined_score for e in evidence) / len(evidence)
        else:
            confidence = 0.0

        # Generate answer based on evidence type
        top_evidence = evidence[:5]  # Top 5 pieces

        # Collect unique entities from evidence
        entity_ids = set()
        entity_names = []

        for ev in top_evidence:
            for entity in ev.entities:
                if entity.id not in entity_ids:
                    entity_ids.add(entity.id)
                    name = entity.properties.get("name", entity.id)
                    entity_type = entity.entity_type
                    entity_names.append(f"{name} ({entity_type})")

        # Build answer
        if len(entity_names) == 0:
            answer = "No relevant entities found."
        elif len(entity_names) == 1:
            answer = f"Found: {entity_names[0]}"
        elif len(entity_names) <= 3:
            answer = f"Found: {', '.join(entity_names)}"
        else:
            answer = f"Found {len(entity_names)} entities: {', '.join(entity_names[:3])}, and {len(entity_names) - 3} more"

        # Add path information if available
        path_count = sum(1 for ev in top_evidence if ev.evidence_type == EvidenceType.PATH)
        if path_count > 0:
            answer += f" (through {path_count} connection{'s' if path_count != 1 else ''})"

        return answer, confidence
