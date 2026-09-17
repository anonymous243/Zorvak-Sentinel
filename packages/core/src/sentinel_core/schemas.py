from datetime import datetime
from enum import StrEnum

class ConflictType(StrEnum):
    OVERLAP = "overlap"
    SHADOWED = "shadowed"
    CONTRADICTION = "contradiction"
    REDUNDANT = "redundant"

class PatternRelationship(StrEnum):
    DISJOINT = "disjoint"
    EQUAL = "equal"
    A_SUBSUMES_B = "a_subsumes_b"
    B_SUBSUMES_A = "b_subsumes_a"
    OVERLAPPING = "overlapping"

from pydantic import BaseModel, ConfigDict, Field


class PolicyEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    provider: str | None = Field(default=None, max_length=64)
    external_id: str | None = Field(default=None, max_length=255)
    environment: str = Field(default="development", max_length=32)


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    provider: str | None
    external_id: str | None
    status: str
    environment: str
    created_at: datetime
    updated_at: datetime


class PolicyCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    effect: PolicyEffect
    priority: int = Field(default=100, ge=0, le=9999)
    action: str = Field(min_length=1, max_length=255)
    resource: str = Field(min_length=1, max_length=255)


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    effect: PolicyEffect
    priority: int
    action: str
    resource: str
    enabled: bool
    created_at: datetime
    updated_at: datetime



class ConflictReport(BaseModel):
    conflict_type: ConflictType
    target_policy_id: str
    target_policy_version_id: str
    conflicting_policy_id: str
    conflicting_policy_version_id: str
    relationship: str
    target_effect: str
    conflicting_effect: str
    target_priority: int
    conflicting_priority: int
    explanation_code: str


from typing import Mapping

class PolicySimulationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    
    agent_id: str = Field(min_length=1, max_length=36)
    tool_id: str = Field(min_length=1, max_length=36)
    action: str = Field(min_length=1, max_length=255)
    resource: str = Field(min_length=1, max_length=255)
    context: Mapping[str, str] = Field(default_factory=dict)
    candidate_policy_version_id: str | None = None


class PolicySimulationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    effect: str
    reason: str
    evaluated_policy_id: str | None = None
    evaluated_policy_version_id: str | None = None
    risk_level: str | None = None
    capability_id: str | None = None
    simulation_ms: float
    candidate_used: bool = False

class PolicyRollbackRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    
    target_version_id: str = Field(min_length=1, max_length=36)

class PolicyRollbackResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    policy_id: str
    previous_active_version_id: str | None
    new_active_version_id: str
    changed: bool
    reason: str

class PolicyAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    tenant_id: str
    policy_id: str
    policy_version_id: str | None
    agent_id: str
    credential_id: str | None
    operation: str
    before_state: str | None
    after_state: str | None
    occurred_at: datetime
    correlation_id: str | None
    request_id: str | None
