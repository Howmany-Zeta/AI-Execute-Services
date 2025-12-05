"""
Knowledge Graph Reasoning Tool

AIECS tool for advanced reasoning over knowledge graphs.
Provides query planning, multi-hop reasoning, inference, and evidence synthesis.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.application.knowledge_graph.reasoning.query_planner import (
    QueryPlanner,
)
from aiecs.application.knowledge_graph.reasoning.reasoning_engine import (
    ReasoningEngine,
)
from aiecs.application.knowledge_graph.reasoning.inference_engine import (
    InferenceEngine,
)
from aiecs.application.knowledge_graph.reasoning.evidence_synthesis import (
    EvidenceSynthesizer,
)
from aiecs.application.knowledge_graph.reasoning.logic_form_parser import (
    LogicFormParser,
)
from aiecs.domain.knowledge_graph.models.inference_rule import (
    InferenceRule,
    RuleType,
)
from aiecs.domain.knowledge_graph.models.query_plan import OptimizationStrategy


class ReasoningModeEnum(str, Enum):
    """Reasoning mode enumeration"""

    QUERY_PLAN = "query_plan"  # Plan a query execution
    MULTI_HOP = "multi_hop"  # Multi-hop path reasoning
    INFERENCE = "inference"  # Logical inference
    EVIDENCE_SYNTHESIS = "evidence_synthesis"  # Combine evidence
    LOGICAL_QUERY = "logical_query"  # Parse natural language to logical query
    FULL_REASONING = "full_reasoning"  # Complete reasoning pipeline


class GraphReasoningInput(BaseModel):
    """Input schema for Graph Reasoning Tool (legacy, for execute() method)"""

    mode: ReasoningModeEnum = Field(
        ...,
        description=(
            "Reasoning mode: 'query_plan' (plan execution), "
            "'multi_hop' (path reasoning), 'inference' (logical rules), "
            "'evidence_synthesis' (combine evidence), "
            "'logical_query' (parse to logical form), "
            "'full_reasoning' (complete pipeline)"
        ),
    )

    query: str = Field(..., description="Natural language query to reason about")

    start_entity_id: Optional[str] = Field(None, description="Starting entity ID for multi-hop reasoning")

    target_entity_id: Optional[str] = Field(None, description="Target entity ID for path finding")

    max_hops: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum hops for multi-hop reasoning (1-5)",
    )

    relation_types: Optional[List[str]] = Field(None, description="Filter by relation types for reasoning")

    optimization_strategy: Optional[str] = Field(
        default="balanced",
        description="Query optimization strategy: 'cost', 'latency', or 'balanced'",
    )

    apply_inference: bool = Field(
        default=False,
        description="Apply logical inference rules (transitive, symmetric)",
    )

    inference_relation_type: Optional[str] = Field(
        None,
        description="Relation type to apply inference on (required if apply_inference=True)",
    )

    inference_max_steps: int = Field(default=3, ge=1, le=10, description="Maximum inference steps (1-10)")

    synthesize_evidence: bool = Field(default=True, description="Synthesize evidence from multiple sources")

    synthesis_method: str = Field(
        default="weighted_average",
        description="Evidence synthesis method: 'weighted_average', 'max', or 'voting'",
    )

    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for evidence (0.0-1.0)",
    )


# Schemas for individual operations (used with run_async)
class QueryPlanSchema(BaseModel):
    """Schema for query_plan operation"""

    query: str = Field(..., description="Natural language query to plan")
    optimization_strategy: Optional[str] = Field(
        default="balanced",
        description="Query optimization strategy: 'cost', 'latency', or 'balanced'",
    )


class MultiHopSchema(BaseModel):
    """Schema for multi_hop operation"""

    query: str = Field(..., description="Natural language query to reason about")
    start_entity_id: str = Field(..., description="Starting entity ID")
    target_entity_id: Optional[str] = Field(None, description="Target entity ID")
    max_hops: int = Field(default=3, ge=1, le=5, description="Maximum hops (1-5)")
    relation_types: Optional[List[str]] = Field(None, description="Filter by relation types")
    synthesize_evidence: bool = Field(default=True, description="Synthesize evidence")
    synthesis_method: str = Field(default="weighted_average", description="Synthesis method")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Min confidence")


class InferenceSchema(BaseModel):
    """Schema for inference operation"""

    relation_type: str = Field(..., description="Relation type to apply inference on")
    max_steps: int = Field(default=3, ge=1, le=10, description="Maximum inference steps")


class EvidenceSynthesisSchema(BaseModel):
    """Schema for evidence_synthesis operation"""

    synthesis_method: str = Field(default="weighted_average", description="Synthesis method")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Min confidence")


class FullReasoningSchema(BaseModel):
    """Schema for full_reasoning operation"""

    query: str = Field(..., description="Natural language query")
    start_entity_id: str = Field(..., description="Starting entity ID")
    target_entity_id: Optional[str] = Field(None, description="Target entity ID")
    max_hops: int = Field(default=3, ge=1, le=5, description="Maximum hops")
    relation_types: Optional[List[str]] = Field(None, description="Filter by relation types")
    optimization_strategy: Optional[str] = Field(default="balanced", description="Optimization strategy")
    apply_inference: bool = Field(default=False, description="Apply logical inference rules")
    inference_relation_type: Optional[str] = Field(None, description="Relation type for inference")
    inference_max_steps: int = Field(default=3, ge=1, le=10, description="Max inference steps")
    synthesize_evidence: bool = Field(default=True, description="Synthesize evidence")
    synthesis_method: str = Field(default="weighted_average", description="Synthesis method")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Min confidence")


@register_tool("graph_reasoning")
class GraphReasoningTool(BaseTool):
    """
    Knowledge Graph Reasoning Tool

    Performs advanced reasoning over knowledge graphs using:
    - Query Planning: Optimize query execution
    - Multi-Hop Reasoning: Find and reason over paths
    - Logical Inference: Apply inference rules
    - Evidence Synthesis: Combine evidence from multiple sources

    Example:
        ```python
        tool = GraphReasoningTool(graph_store)

        result = await tool.execute({
            "mode": "full_reasoning",
            "query": "How is Alice connected to Company X?",
            "start_entity_id": "alice",
            "max_hops": 3,
            "apply_inference": True,
            "synthesize_evidence": True
        })
        ```
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the Graph Reasoning Tool
        
        Automatically reads from environment variables with GRAPH_REASONING_ prefix.
        Example: GRAPH_REASONING_DEFAULT_MAX_HOPS -> default_max_hops
        """

        model_config = SettingsConfigDict(env_prefix="GRAPH_REASONING_")

        default_max_hops: int = Field(
            default=3,
            description="Default maximum hops for multi-hop reasoning",
        )
        default_confidence_threshold: float = Field(
            default=0.5,
            description="Default confidence threshold for evidence",
        )
        default_inference_max_steps: int = Field(
            default=3,
            description="Default maximum inference steps",
        )
        enable_default_rules: bool = Field(
            default=False,
            description="Enable default inference rules by default",
        )

    def __init__(self, graph_store: Optional[GraphStore] = None, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize Graph Reasoning Tool

        Args:
            graph_store: Graph storage backend (optional, can be set via _initialize())
            config (Dict, optional): Configuration overrides for Graph Reasoning Tool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/graph_reasoning.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Note:
            If graph_store is not provided, you must call _initialize() before using
            the tool. This allows the tool to be registered and instantiated via
            get_tool() without requiring a graph_store at import time.
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        # Initialize components (may be None if graph_store not provided)
        self.graph_store = graph_store
        self.query_planner = None
        self.reasoning_engine = None
        self.inference_engine = None
        self.evidence_synthesizer = None
        self._initialized = False

        # If graph_store provided, initialize immediately (backward compatibility)
        if graph_store is not None:
            self._setup_components(graph_store)

    def _setup_components(self, graph_store: GraphStore) -> None:
        """Setup reasoning components with the given graph store."""
        self.graph_store = graph_store
        self.query_planner = QueryPlanner(graph_store)
        self.reasoning_engine = ReasoningEngine(graph_store)
        self.inference_engine = InferenceEngine(graph_store)
        self.evidence_synthesizer = EvidenceSynthesizer()

        # Add default inference rules
        self._setup_default_rules()
        self._initialized = True

    async def _initialize(self, graph_store: Optional[GraphStore] = None) -> None:
        """
        Lazy initialization of components.

        Args:
            graph_store: Graph storage backend. If not provided, creates an
                        InMemoryGraphStore.
        """
        if self._initialized:
            return

        # Use provided graph_store or create a default one
        if graph_store is None:
            from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
            graph_store = InMemoryGraphStore()
            await graph_store.initialize()

        self._setup_components(graph_store)

    def _setup_default_rules(self):
        """Setup default inference rules"""
        # Common transitive rules
        transitive_relations = [
            "KNOWS",
            "FOLLOWS",
            "CONNECTED_TO",
            "RELATED_TO",
        ]
        for rel_type in transitive_relations:
            self.inference_engine.add_rule(
                InferenceRule(
                    rule_id=f"transitive_{rel_type.lower()}",
                    rule_type=RuleType.TRANSITIVE,
                    relation_type=rel_type,
                    description=f"Transitive closure for {rel_type}",
                    confidence_decay=0.1,
                    enabled=False,  # Only enable when requested
                )
            )

        # Common symmetric rules
        symmetric_relations = [
            "FRIEND_OF",
            "COLLEAGUE_OF",
            "PARTNER_WITH",
            "SIBLING_OF",
        ]
        for rel_type in symmetric_relations:
            self.inference_engine.add_rule(
                InferenceRule(
                    rule_id=f"symmetric_{rel_type.lower()}",
                    rule_type=RuleType.SYMMETRIC,
                    relation_type=rel_type,
                    description=f"Symmetric relationship for {rel_type}",
                    confidence_decay=0.05,
                    enabled=False,  # Only enable when requested
                )
            )

    @property
    def name(self) -> str:
        return "graph_reasoning"

    @property
    def description(self) -> str:
        return "Advanced reasoning over knowledge graphs with query planning, multi-hop reasoning, inference, and evidence synthesis"

    @property
    def input_schema(self) -> type[GraphReasoningInput]:
        return GraphReasoningInput

    async def _execute(self, validated_input: GraphReasoningInput) -> Dict[str, Any]:
        """
        Execute reasoning based on mode

        Args:
            validated_input: Validated input parameters

        Returns:
            Reasoning results

        Raises:
            RuntimeError: If tool is not initialized (call _initialize() first)
        """
        if not self._initialized:
            raise RuntimeError(
                "GraphReasoningTool is not initialized. "
                "Call await tool._initialize(graph_store) first, or provide "
                "graph_store in the constructor."
            )

        mode = validated_input.mode

        if mode == ReasoningModeEnum.QUERY_PLAN:
            return await self._execute_query_plan(validated_input)

        elif mode == ReasoningModeEnum.MULTI_HOP:
            return await self._execute_multi_hop(validated_input)

        elif mode == ReasoningModeEnum.INFERENCE:
            return await self._execute_inference(validated_input)

        elif mode == ReasoningModeEnum.EVIDENCE_SYNTHESIS:
            return await self._execute_evidence_synthesis(validated_input)

        elif mode == ReasoningModeEnum.LOGICAL_QUERY:
            return await self._execute_logical_query(validated_input)

        elif mode == ReasoningModeEnum.FULL_REASONING:
            return await self._execute_full_reasoning(validated_input)

        else:
            raise ValueError(f"Unknown reasoning mode: {mode}")

    async def _execute_query_plan(self, input_data: GraphReasoningInput) -> Dict[str, Any]:
        """Execute query planning"""
        # Plan the query (not async)
        plan = self.query_planner.plan_query(input_data.query)

        # Optimize if strategy provided
        strategy_map = {
            "cost": OptimizationStrategy.MINIMIZE_COST,
            "latency": OptimizationStrategy.MINIMIZE_LATENCY,
            "balanced": OptimizationStrategy.BALANCED,
        }
        strategy_key = input_data.optimization_strategy or "balanced"
        strategy = strategy_map.get(strategy_key, OptimizationStrategy.BALANCED)
        optimized_plan = self.query_planner.optimize_plan(plan, strategy)

        return {
            "mode": "query_plan",
            "query": input_data.query,
            "plan": {
                "steps": [
                    {
                        "step_id": step.step_id,
                        "operation": step.operation.value,
                        "depends_on": step.depends_on,
                        "estimated_cost": step.estimated_cost,
                        "description": step.description,
                    }
                    for step in optimized_plan.steps
                ],
                "total_cost": optimized_plan.calculate_total_cost(),
                "estimated_latency_ms": optimized_plan.calculate_total_cost() * 100,  # Rough estimate
                "optimization_strategy": strategy.value,
            },
        }

    async def _execute_multi_hop(self, input_data: GraphReasoningInput) -> Dict[str, Any]:
        """Execute multi-hop reasoning"""
        if not input_data.start_entity_id:
            raise ValueError("start_entity_id is required for multi-hop reasoning")

        # Build context for reasoning
        context: Dict[str, Any] = {}
        if input_data.start_entity_id:
            context["start_entity_id"] = input_data.start_entity_id
        if input_data.target_entity_id:
            context["target_entity_id"] = input_data.target_entity_id
        if input_data.relation_types:
            context["relation_types"] = input_data.relation_types

        # Execute reasoning
        result = await self.reasoning_engine.reason(
            query=input_data.query,
            context=context,
            max_hops=input_data.max_hops,
        )

        # Optionally synthesize evidence
        evidence_list = result.evidence
        if input_data.synthesize_evidence and evidence_list:
            evidence_list = self.evidence_synthesizer.synthesize_evidence(evidence_list, method=input_data.synthesis_method)
            # Filter by confidence
            evidence_list = self.evidence_synthesizer.filter_by_confidence(evidence_list, threshold=input_data.confidence_threshold)

        return {
            "mode": "multi_hop",
            "query": input_data.query,
            "answer": result.answer,
            "confidence": result.confidence,
            "evidence_count": len(evidence_list),
            "evidence": [
                {
                    "evidence_id": ev.evidence_id,
                    "type": ev.evidence_type.value,
                    "confidence": ev.confidence,
                    "relevance_score": ev.relevance_score,
                    "explanation": ev.explanation,
                    "entity_ids": ev.get_entity_ids(),
                }
                for ev in evidence_list[:10]  # Limit to top 10
            ],
            "execution_time_ms": result.execution_time_ms,
            "reasoning_trace": result.reasoning_trace,
        }

    async def _execute_inference(self, input_data: GraphReasoningInput) -> Dict[str, Any]:
        """Execute logical inference"""
        if not input_data.apply_inference:
            raise ValueError("apply_inference must be True for inference mode")

        if not input_data.inference_relation_type:
            raise ValueError("inference_relation_type is required for inference mode")

        # Enable the relevant rules
        for rule in self.inference_engine.get_rules(input_data.inference_relation_type):
            rule.enabled = True

        # Apply inference
        result = await self.inference_engine.infer_relations(
            relation_type=input_data.inference_relation_type,
            max_steps=input_data.inference_max_steps,
            use_cache=True,
        )

        # Get trace
        trace = self.inference_engine.get_inference_trace(result)

        return {
            "mode": "inference",
            "relation_type": input_data.inference_relation_type,
            "inferred_count": len(result.inferred_relations),
            "inferred_relations": [
                {
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "relation_type": rel.relation_type,
                    "properties": rel.properties,
                }
                for rel in result.inferred_relations[:10]  # Limit to top 10
            ],
            "confidence": result.confidence,
            "total_steps": result.total_steps,
            "inference_trace": trace[:20],  # Limit trace lines
        }

    async def _execute_evidence_synthesis(self, input_data: GraphReasoningInput) -> Dict[str, Any]:
        """Execute evidence synthesis (requires pre-collected evidence)"""
        # This mode is for synthesizing already collected evidence
        # In practice, evidence would come from a previous reasoning step

        return {
            "mode": "evidence_synthesis",
            "message": "Evidence synthesis requires pre-collected evidence. Use 'full_reasoning' mode for end-to-end reasoning with synthesis.",
            "synthesis_method": input_data.synthesis_method,
            "confidence_threshold": input_data.confidence_threshold,
        }

    async def _execute_logical_query(self, input_data: GraphReasoningInput) -> Dict[str, Any]:
        """
        Parse natural language query to logical form

        Converts natural language queries into structured logical representations
        that can be executed against the knowledge graph.

        Args:
            input_data: Reasoning input with query

        Returns:
            Dictionary with parsed logical query
        """
        # Create logic form parser
        parser = LogicFormParser()

        # Parse query to logical form
        logical_query = parser.parse(input_data.query)

        # Extract components
        result = {
            "mode": "logical_query",
            "query": input_data.query,
            "logical_form": logical_query.to_dict(),
            "query_type": logical_query.query_type.value,
            "variables": [v.name for v in logical_query.variables],
            "predicates": [
                {
                    "name": p.name,
                    "arguments": [arg.name if hasattr(arg, "name") else str(arg) for arg in p.arguments],
                }
                for p in logical_query.predicates
            ],
            "constraints": [
                {
                    "type": c.constraint_type.value if hasattr(c.constraint_type, "value") else str(c.constraint_type),
                    "variable": c.variable.name,
                    "value": c.value,
                }
                for c in logical_query.constraints
            ],
        }

        # Add execution plan if available
        if hasattr(logical_query, "execution_plan"):
            result["execution_plan"] = {
                "steps": len(logical_query.execution_plan.steps),
                "estimated_cost": logical_query.execution_plan.calculate_total_cost(),
            }

        return result

    async def _execute_full_reasoning(self, input_data: GraphReasoningInput) -> Dict[str, Any]:
        """Execute full reasoning pipeline"""
        if not input_data.start_entity_id:
            raise ValueError("start_entity_id is required for full reasoning")

        results: Dict[str, Any] = {
            "mode": "full_reasoning",
            "query": input_data.query,
            "steps": [],
        }

        # Step 1: Query Planning
        plan = self.query_planner.plan_query(input_data.query)
        strategy_map = {
            "cost": OptimizationStrategy.MINIMIZE_COST,
            "latency": OptimizationStrategy.MINIMIZE_LATENCY,
            "balanced": OptimizationStrategy.BALANCED,
        }
        strategy_key = input_data.optimization_strategy or "balanced"
        strategy = strategy_map.get(strategy_key, OptimizationStrategy.BALANCED)
        optimized_plan = self.query_planner.optimize_plan(plan, strategy)

        results["steps"].append(
            {
                "name": "query_planning",
                "plan_steps": len(optimized_plan.steps),
                "estimated_cost": optimized_plan.calculate_total_cost(),
                "estimated_latency_ms": optimized_plan.calculate_total_cost() * 100,  # Rough estimate
            }
        )

        # Step 2: Multi-Hop Reasoning
        # Build context for reasoning
        context: Dict[str, Any] = {}
        if input_data.start_entity_id:
            context["start_entity_id"] = input_data.start_entity_id
        if input_data.target_entity_id:
            context["target_entity_id"] = input_data.target_entity_id
        if input_data.relation_types:
            context["relation_types"] = input_data.relation_types

        reasoning_result = await self.reasoning_engine.reason(
            query=input_data.query,
            context=context,
            max_hops=input_data.max_hops,
        )

        results["steps"].append(
            {
                "name": "multi_hop_reasoning",
                "evidence_collected": len(reasoning_result.evidence),
                "confidence": reasoning_result.confidence,
                "execution_time_ms": reasoning_result.execution_time_ms,
            }
        )

        # Step 3: Logical Inference (if requested)
        if input_data.apply_inference and input_data.inference_relation_type:
            # Enable rules
            for rule in self.inference_engine.get_rules(input_data.inference_relation_type):
                rule.enabled = True

            inference_result = await self.inference_engine.infer_relations(
                relation_type=input_data.inference_relation_type,
                max_steps=input_data.inference_max_steps,
                use_cache=True,
            )

            results["steps"].append(
                {
                    "name": "logical_inference",
                    "inferred_relations": len(inference_result.inferred_relations),
                    "inference_confidence": inference_result.confidence,
                    "inference_steps": inference_result.total_steps,
                }
            )

        # Step 4: Evidence Synthesis
        evidence_list = reasoning_result.evidence
        if input_data.synthesize_evidence and evidence_list:
            synthesized = self.evidence_synthesizer.synthesize_evidence(evidence_list, method=input_data.synthesis_method)

            filtered = self.evidence_synthesizer.filter_by_confidence(synthesized, threshold=input_data.confidence_threshold)

            ranked = self.evidence_synthesizer.rank_by_reliability(filtered)

            overall_confidence = self.evidence_synthesizer.estimate_overall_confidence(ranked)

            results["steps"].append(
                {
                    "name": "evidence_synthesis",
                    "original_evidence": len(evidence_list),
                    "synthesized_evidence": len(synthesized),
                    "filtered_evidence": len(filtered),
                    "overall_confidence": overall_confidence,
                }
            )

            evidence_list = ranked

        # Final Results
        results["answer"] = reasoning_result.answer
        results["final_confidence"] = self.evidence_synthesizer.estimate_overall_confidence(evidence_list) if evidence_list else reasoning_result.confidence
        results["evidence_count"] = len(evidence_list)
        # Create top evidence list
        top_evidence_list: List[Dict[str, Any]] = [
            {
                "evidence_id": ev.evidence_id,
                "type": ev.evidence_type.value,
                "confidence": ev.confidence,
                "relevance_score": ev.relevance_score,
                "explanation": ev.explanation,
            }
            for ev in evidence_list[:5]  # Top 5
        ]
        results["top_evidence"] = top_evidence_list
        # Limit trace
        results["reasoning_trace"] = reasoning_result.reasoning_trace[:10]

        return results

    # Public methods for ToolExecutor integration
    async def query_plan(self, query: str, optimization_strategy: Optional[str] = "balanced") -> Dict[str, Any]:
        """Query planning (public method for ToolExecutor)"""
        input_data = GraphReasoningInput(
            mode=ReasoningModeEnum.QUERY_PLAN,
            query=query,
            optimization_strategy=optimization_strategy,
            start_entity_id="dummy",  # Not used for query_plan
            target_entity_id=None,
            relation_types=None,
            inference_relation_type=None,
        )
        return await self._execute_query_plan(input_data)

    async def multi_hop(
        self,
        query: str,
        start_entity_id: str,
        target_entity_id: Optional[str] = None,
        max_hops: int = 3,
        relation_types: Optional[List[str]] = None,
        synthesize_evidence: bool = True,
        synthesis_method: str = "weighted_average",
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Multi-hop reasoning (public method for ToolExecutor)"""
        input_data = GraphReasoningInput(
            mode=ReasoningModeEnum.MULTI_HOP,
            query=query,
            start_entity_id=start_entity_id,
            target_entity_id=target_entity_id,
            max_hops=max_hops,
            relation_types=relation_types,
            inference_relation_type=None,
            synthesize_evidence=synthesize_evidence,
            synthesis_method=synthesis_method,
            confidence_threshold=confidence_threshold,
        )
        return await self._execute_multi_hop(input_data)

    async def inference(self, relation_type: str, max_steps: int = 3) -> Dict[str, Any]:
        """Logical inference (public method for ToolExecutor)"""
        input_data = GraphReasoningInput(
            mode=ReasoningModeEnum.INFERENCE,
            query="inference",  # Not used for inference mode
            start_entity_id="dummy",  # Not used for inference mode
            apply_inference=True,
            inference_relation_type=relation_type,
            inference_max_steps=max_steps,
            target_entity_id=None,
            relation_types=None,
        )
        return await self._execute_inference(input_data)

    async def evidence_synthesis(
        self,
        synthesis_method: str = "weighted_average",
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Evidence synthesis (public method for ToolExecutor)"""
        input_data = GraphReasoningInput(
            mode=ReasoningModeEnum.EVIDENCE_SYNTHESIS,
            query="synthesis",  # Not used
            start_entity_id="dummy",  # Not used
            synthesis_method=synthesis_method,
            target_entity_id=None,
            relation_types=None,
            inference_relation_type=None,
            confidence_threshold=confidence_threshold,
        )
        return await self._execute_evidence_synthesis(input_data)

    async def full_reasoning(
        self,
        query: str,
        start_entity_id: str,
        target_entity_id: Optional[str] = None,
        max_hops: int = 3,
        relation_types: Optional[List[str]] = None,
        optimization_strategy: Optional[str] = "balanced",
        apply_inference: bool = False,
        inference_relation_type: Optional[str] = None,
        inference_max_steps: int = 3,
        synthesize_evidence: bool = True,
        synthesis_method: str = "weighted_average",
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Full reasoning pipeline (public method for ToolExecutor)"""
        input_data = GraphReasoningInput(
            mode=ReasoningModeEnum.FULL_REASONING,
            query=query,
            start_entity_id=start_entity_id,
            target_entity_id=target_entity_id,
            max_hops=max_hops,
            relation_types=relation_types,
            optimization_strategy=optimization_strategy,
            apply_inference=apply_inference,
            inference_relation_type=inference_relation_type,
            inference_max_steps=inference_max_steps,
            synthesize_evidence=synthesize_evidence,
            synthesis_method=synthesis_method,
            confidence_threshold=confidence_threshold,
        )
        return await self._execute_full_reasoning(input_data)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool (public interface)

        Args:
            **kwargs: Tool input parameters (will be validated against input_schema)

        Returns:
            Dictionary with reasoning results
        """
        # Validate input using Pydantic schema
        validated_input = self.input_schema(**kwargs)
        return await self._execute(validated_input)
