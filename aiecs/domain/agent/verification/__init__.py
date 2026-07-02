# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""GVR verification primitives (A-1)."""

from aiecs.domain.agent.exceptions import VerificationExhausted
from .context_builder import build_verification_context
from .criteria import normalize_acceptance_criteria
from .models import (
    AcceptanceCriterion,
    EvidenceItem,
    FeedbackItem,
    Verdict,
    VerificationContext,
    VerdictKind,
)
from .read_only_verifier import ReadOnlyAdversarialVerifier
from .peer_review_policy_models import PeerReviewPolicy
from .peer_review import (
    build_peer_review_task,
    peer_review_response_to_verdict,
)
from .policy_models import VerificationPolicy, WhenToVerify
from .policy_runner import run_gvr_pre_exit, run_verification_policy
from .dawp_result import DAWPResult, build_dawp_result, dawp_result_terminal_event
from .cwe_verifier import (
    CweVerifier,
    build_cwe_verifier_from_config,
    is_h1_goal,
    run_dual_spawn_verifier_path,
)
from .cwe_verifier_policy_models import CweVerifierPolicy, resolve_cwe_verifier_policy
from .review_refinement import REVIEW_REFINEMENT_TEMPLATE, build_review_refinement_task
from .verifier import Verifier, merge_verdicts
from .gates import (
    AggregatedGateScore,
    CitationUrlGate,
    DeterministicGate,
    GateRegistry,
    GateScore,
    SpecGate,
    build_gate_registry_from_config,
    gate_aggregate_to_verdict,
)

__all__ = [
    "AcceptanceCriterion",
    "EvidenceItem",
    "FeedbackItem",
    "Verdict",
    "VerdictKind",
    "VerificationContext",
    "Verifier",
    "ReadOnlyAdversarialVerifier",
    "VerificationPolicy",
    "WhenToVerify",
    "PeerReviewPolicy",
    "build_peer_review_task",
    "peer_review_response_to_verdict",
    "DAWPResult",
    "build_dawp_result",
    "dawp_result_terminal_event",
    "CweVerifier",
    "CweVerifierPolicy",
    "build_cwe_verifier_from_config",
    "run_dual_spawn_verifier_path",
    "is_h1_goal",
    "resolve_cwe_verifier_policy",
    "REVIEW_REFINEMENT_TEMPLATE",
    "build_review_refinement_task",
    "VerificationExhausted",
    "run_gvr_pre_exit",
    "run_verification_policy",
    "build_verification_context",
    "merge_verdicts",
    "normalize_acceptance_criteria",
    "AggregatedGateScore",
    "CitationUrlGate",
    "DeterministicGate",
    "GateRegistry",
    "GateScore",
    "SpecGate",
    "build_gate_registry_from_config",
    "gate_aggregate_to_verdict",
]
