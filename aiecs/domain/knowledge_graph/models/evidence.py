"""
Evidence Domain Models

Models for representing evidence from reasoning processes.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path


class EvidenceType(str, Enum):
    """Types of evidence"""

    ENTITY = "entity"  # Single entity
    RELATION = "relation"  # Single relation
    PATH = "path"  # Complete path
    SUBGRAPH = "subgraph"  # Subgraph fragment


class Evidence(BaseModel):
    """
    Evidence from Reasoning

    Represents a piece of evidence collected during reasoning,
    with confidence scoring and provenance tracking.

    Attributes:
        evidence_id: Unique identifier for this evidence
        evidence_type: Type of evidence (entity, relation, path, etc.)
        entities: Entities involved in this evidence
        relations: Relations involved in this evidence
        paths: Paths involved in this evidence (for path-based evidence)
        confidence: Confidence score (0-1, higher = more confident)
        relevance_score: Relevance to the query (0-1)
        explanation: Human-readable explanation of this evidence
        source: Source of this evidence (e.g., "traversal", "vector_search")
        metadata: Additional metadata

    Example:
        ```python
        evidence = Evidence(
            evidence_id="ev_001",
            evidence_type=EvidenceType.PATH,
            entities=[alice, bob, company],
            relations=[knows_rel, works_at_rel],
            paths=[path],
            confidence=0.9,
            relevance_score=0.85,
            explanation="Alice knows Bob who works at Company X",
            source="multi_hop_traversal"
        )
        ```
    """

    evidence_id: str = Field(..., description="Unique identifier for this evidence")

    evidence_type: EvidenceType = Field(..., description="Type of evidence")

    entities: List[Entity] = Field(default_factory=list, description="Entities involved in this evidence")

    relations: List[Relation] = Field(default_factory=list, description="Relations involved in this evidence")

    paths: List[Path] = Field(default_factory=list, description="Paths involved in this evidence")

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1, higher = more confident)",
    )

    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Relevance to the query (0-1)")

    explanation: str = Field(default="", description="Human-readable explanation of this evidence")

    source: str = Field(default="", description="Source of this evidence (e.g., query step ID)")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def combined_score(self) -> float:
        """Get combined score (confidence * relevance)"""
        return self.confidence * self.relevance_score

    def get_entity_ids(self) -> List[str]:
        """Get list of all entity IDs in evidence"""
        return [entity.id for entity in self.entities]

    def __str__(self) -> str:
        return f"Evidence(type={self.evidence_type}, " f"score={self.combined_score:.2f}, " f"entities={len(self.entities)})"


class ReasoningResult(BaseModel):
    """
    Result of Reasoning Process

    Contains evidence collected, answer generated, and reasoning trace.

    Attributes:
        query: Original query that was answered
        evidence: List of evidence pieces collected
        answer: Generated answer (if applicable)
        confidence: Overall confidence in the answer (0-1)
        reasoning_trace: Human-readable trace of reasoning steps
        execution_time_ms: Time taken to perform reasoning
        metadata: Additional metadata

    Example:
        ```python
        result = ReasoningResult(
            query="What companies does Alice know people at?",
            evidence=[ev1, ev2, ev3],
            answer="Alice knows people at Company X and Company Y",
            confidence=0.87,
            reasoning_trace="Step 1: Find Alice\nStep 2: Find people Alice knows\n...",
            execution_time_ms=125.5
        )
        ```
    """

    query: str = Field(..., description="Original query that was answered")

    evidence: List[Evidence] = Field(default_factory=list, description="List of evidence pieces collected")

    answer: Optional[str] = Field(default=None, description="Generated answer (if applicable)")

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the answer (0-1)",
    )

    reasoning_trace: List[str] = Field(default_factory=list, description="List of reasoning steps taken")

    execution_time_ms: Optional[float] = Field(default=None, ge=0.0, description="Time taken to perform reasoning")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def evidence_count(self) -> int:
        """Get number of evidence pieces"""
        return len(self.evidence)

    @property
    def has_answer(self) -> bool:
        """Check if result has an answer"""
        return self.answer is not None and len(self.answer) > 0

    def get_top_evidence(self, n: int = 5) -> List[Evidence]:
        """
        Get top N evidence pieces by combined score

        Args:
            n: Number of evidence pieces to return

        Returns:
            Top N evidence pieces
        """
        sorted_evidence = sorted(self.evidence, key=lambda e: e.combined_score, reverse=True)
        return sorted_evidence[:n]

    def get_trace_string(self) -> str:
        """Get reasoning trace as a single string"""
        return "\n".join(self.reasoning_trace)

    def __str__(self) -> str:
        parts = [
            f"ReasoningResult(evidence={self.evidence_count}",
            f"confidence={self.confidence:.2f})",
        ]
        if self.has_answer and self.answer:
            parts.insert(1, f"answer={self.answer[:50]}...")
        return " ".join(parts)
