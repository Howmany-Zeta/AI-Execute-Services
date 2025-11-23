"""
Inference Rule Domain Models

Models for representing logical inference rules.
"""

from typing import List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.models.relation import Relation


class RuleType(str, Enum):
    """Types of inference rules"""

    TRANSITIVE = "transitive"  # A->B, B->C => A->C
    SYMMETRIC = "symmetric"  # A->B => B->A
    REFLEXIVE = "reflexive"  # A => A->A
    CUSTOM = "custom"  # User-defined rule


class InferenceRule(BaseModel):
    """
    Inference Rule

    Represents a logical rule for inferring new relations from existing ones.

    Attributes:
        rule_id: Unique identifier for this rule
        rule_type: Type of rule (transitive, symmetric, etc.)
        relation_type: Relation type this rule applies to
        description: Human-readable description
        enabled: Whether this rule is enabled
        confidence_decay: How much confidence decreases with each inference step (0-1)
        metadata: Additional metadata

    Example:
        ```python
        rule = InferenceRule(
            rule_id="rule_001",
            rule_type=RuleType.TRANSITIVE,
            relation_type="WORKS_FOR",
            description="If A works for B and B works for C, then A works for C",
            confidence_decay=0.1
        )
        ```
    """

    rule_id: str = Field(..., description="Unique identifier for this rule")

    rule_type: RuleType = Field(..., description="Type of inference rule")

    relation_type: str = Field(..., description="Relation type this rule applies to")

    description: str = Field(default="", description="Human-readable description of the rule")

    enabled: bool = Field(default=True, description="Whether this rule is enabled")

    confidence_decay: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Confidence decay per inference step (0-1)",
    )

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def can_apply(self, relation: Relation) -> bool:
        """
        Check if this rule can apply to a given relation

        Args:
            relation: Relation to check

        Returns:
            True if rule can apply
        """
        if not self.enabled:
            return False
        return relation.relation_type == self.relation_type


class InferenceStep(BaseModel):
    """
    Single Inference Step

    Represents one step in an inference chain, tracking what was inferred
    and how.

    Attributes:
        step_id: Unique identifier for this step
        inferred_relation: The relation that was inferred
        source_relations: Relations used to infer this one
        rule: The rule that was applied
        confidence: Confidence in this inference (0-1)
        explanation: Human-readable explanation

    Example:
        ```python
        step = InferenceStep(
            step_id="step_001",
            inferred_relation=inferred_rel,
            source_relations=[rel1, rel2],
            rule=rule,
            confidence=0.9,
            explanation="Inferred from transitive rule"
        )
        ```
    """

    step_id: str = Field(..., description="Unique identifier for this step")

    inferred_relation: Relation = Field(..., description="The relation that was inferred")

    source_relations: List[Relation] = Field(..., description="Relations used to infer this one")

    rule: InferenceRule = Field(..., description="The rule that was applied")

    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this inference (0-1)")

    explanation: str = Field(default="", description="Human-readable explanation of the inference")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class InferenceResult(BaseModel):
    """
    Inference Result

    Contains the results of applying inference rules.

    Attributes:
        inferred_relations: List of relations that were inferred
        inference_steps: List of inference steps taken
        total_steps: Total number of inference steps
        confidence: Overall confidence in the results
        explanation: Human-readable explanation

    Example:
        ```python
        result = InferenceResult(
            inferred_relations=[rel1, rel2],
            inference_steps=[step1, step2],
            total_steps=2,
            confidence=0.85,
            explanation="Inferred 2 relations using transitive rule"
        )
        ```
    """

    inferred_relations: List[Relation] = Field(
        default_factory=list,
        description="List of relations that were inferred",
    )

    inference_steps: List[InferenceStep] = Field(default_factory=list, description="List of inference steps taken")

    total_steps: int = Field(default=0, ge=0, description="Total number of inference steps")

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the results",
    )

    explanation: str = Field(default="", description="Human-readable explanation")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def has_results(self) -> bool:
        """Check if any relations were inferred"""
        return len(self.inferred_relations) > 0

    def get_explanation_string(self) -> str:
        """Get explanation as a single string"""
        if not self.explanation:
            return f"Inferred {len(self.inferred_relations)} relations in {self.total_steps} steps"
        return self.explanation

    def get_step_explanations(self) -> List[str]:
        """Get explanations for each step"""
        return [step.explanation for step in self.inference_steps]
