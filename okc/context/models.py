"""Context-Aware Reasoning core objects.

Locked contracts: design/context-aware-reasoning/
Implementation must not deviate without explicit confirmation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ValueType(str, Enum):
    CONTROLLED_VOCABULARY = "controlled_vocabulary"
    RANGE = "range"
    BOOLEAN = "boolean"
    STRING = "string"
    STRUCTURED = "structured"


class Sensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResolutionPolicy(str, Enum):
    REQUIRE_EVIDENCE = "require_evidence"
    ALLOW_ASSUMPTION = "allow_assumption"
    DOMAIN_RULE = "domain_rule"


class CompatibilityState(str, Enum):
    FULLY_COMPATIBLE = "fully_compatible"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    INCOMPATIBLE = "incompatible"
    UNCONSTRAINED = "unconstrained"


class AffordanceAvailability(str, Enum):
    AVAILABLE = "available"
    RETRIEVABLE = "retrievable"
    UNSUPPORTED = "unsupported"


class ContextDimension(BaseModel):
    """Governed definition of a contextual dimension.

    Canonical ownership: global registry or domain plugin only.
    KnowledgePackage may declare support; it may never own or redefine.
    """

    dimension_id: str
    version: str
    value_type: ValueType
    sensitivity: Sensitivity
    resolution_policy: ResolutionPolicy
    can_be_assumed: bool = False
    allowed_values: List[str] = Field(default_factory=list)
    description: str = ""

    model_config = {"frozen": True}


class ParameterStatus(str, Enum):
    PRESENT = "present"
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"


class QueryParameter(BaseModel):
    dimension_id: str
    status: ParameterStatus
    value: Optional[Any] = None
    assumption: Optional[Any] = None
    source: Optional[str] = None  # "evidence" | "user" | "assumption"


class QueryContextEnvelope(BaseModel):
    """Query-specific runtime object. Not part of permanent KnowledgePackage.

    Assumptions never auto-promote. Snapshots immutable.
    """

    envelope_id: str
    revision: int
    parent_revision: Optional[int] = None
    query_id: str
    package_ref: str
    parameters: Dict[str, QueryParameter] = Field(default_factory=dict)
    evidence_set_ref: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    open_high_sensitivity: bool = Field(default=False)  # derived, never independent truth

    def derive_open_high_sensitivity(self, registry: "ContextRegistry") -> bool:
        for param in self.parameters.values():
            dim = registry.get(param.dimension_id)
            if dim and dim.sensitivity == Sensitivity.HIGH:
                if param.status in (ParameterStatus.MISSING, ParameterStatus.PARTIALLY_RESOLVED):
                    return True
        return False


class ExpansionAffordance(BaseModel):
    """Structured, evidence-backed continuation action.

    Only emitted when availability is available or retrievable.
    """

    affordance_id: str
    dimension_id: str
    target_value: Any
    availability: AffordanceAvailability
    effect: str  # constrain | replace_assumption | add_evidence
    source_envelope_id: str
    source_revision: int
    evidence_set_ref: Optional[str] = None
    projected_change: Optional[str] = None  # estimate only
    cost: Optional[str] = None

    @field_validator("availability")
    @classmethod
    def reject_unsupported(cls, v: AffordanceAvailability) -> AffordanceAvailability:
        if v == AffordanceAvailability.UNSUPPORTED:
            raise ValueError("Unsupported affordances must never be emitted")
        return v
