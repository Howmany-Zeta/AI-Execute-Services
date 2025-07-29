"""
Quality Control (QC) Module

This module provides quality control services for multi-task execution,
including examination and acceptance of task outcomes.
"""

from .examine_outcome import (
    ExamineOutcomeService,
    ExaminationRequest,
    ExaminationResult
)
from .accept_outcome import (
    AcceptOutcomeService,
    AcceptanceRequest,
    AcceptanceResult
)

__all__ = [
    "ExamineOutcomeService",
    "ExaminationRequest",
    "ExaminationResult",
    "AcceptOutcomeService",
    "AcceptanceRequest",
    "AcceptanceResult"
]
