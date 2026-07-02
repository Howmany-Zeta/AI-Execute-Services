# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Deterministic gate registry for GVR pre-exit scoring (A-4)."""

from .citation_url_gate import CitationUrlGate
from .conversion import gate_aggregate_to_verdict
from .models import AggregatedGateScore, GateScore
from .protocol import DeterministicGate
from .registry import GateRegistry, build_gate_registry_from_config
from .spec_gate import SpecGate

__all__ = [
    "AggregatedGateScore",
    "CitationUrlGate",
    "DeterministicGate",
    "GateRegistry",
    "GateScore",
    "SpecGate",
    "build_gate_registry_from_config",
    "gate_aggregate_to_verdict",
]
