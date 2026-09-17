import json
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

class AuthorizationDecisionEvent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    event_id: UUID
    event_type: str = Field(default="authorization.decision")
    schema_version: int = Field(default=2)
    
    decision_id: UUID
    request_id: UUID
    tenant_id: str = Field(..., min_length=1, max_length=36)
    credential_id: str = Field(..., min_length=1, max_length=36)
    agent_id: str = Field(..., min_length=1, max_length=36)
    action: str = Field(..., min_length=1)
    resource: str = Field(..., min_length=1)
    effect: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    
    policy_id: Optional[UUID] = None
    policy_version_id: Optional[UUID] = None
    risk_assessment_id: Optional[UUID] = None
    tool_id: Optional[str] = None
    capability_id: Optional[str] = None
    
    evaluated_at: datetime
    evaluation_ms: float = Field(..., ge=0)
    occurred_at: datetime

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v != "authorization.decision":
            raise ValueError("event_type must be 'authorization.decision'")
        return v

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("schema_version must be 1 or 2")
        return v
        
    @field_validator("effect")
    @classmethod
    def validate_effect(cls, v: str) -> str:
        valid_effects = {"allow", "deny"}
        if v not in valid_effects:
            raise ValueError(f"effect must be one of {valid_effects}")
        return v


import json

def serialize_event(event: BaseModel) -> str:
    """
    Deterministically serializes the event to a JSON string.
    Keys are sorted, separators are compact, and non-ASCII characters are safely encoded.
    """
    payload_dict = event.model_dump(mode='json')
    return json.dumps(
        payload_dict,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True
    )


class ActionExecutionEvent(BaseModel):
    """
    Immutable representation of an execution state change.
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )
    
    event_type: Literal["action.execution"] = Field(default="action.execution")
    event_id: UUID = Field(default_factory=uuid4)
    schema_version: int = Field(default=2)
    
    execution_id: UUID
    request_id: UUID
    decision_id: UUID
    risk_assessment_id: UUID | None = None
    
    tenant_id: str
    agent_id: str
    
    action: str
    resource: str
    
    tool_id: str | None = None
    capability_id: str | None = None
    
    status: str
    policy_id: str | None = None
    policy_version_id: str | None = None
    
    occurred_at: datetime


class ActionReconciliationEvent(BaseModel):
    """
    Immutable representation of a reconciliation outcome.
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )
    
    event_type: Literal["action.execution.reconciled"] = Field(default="action.execution.reconciled")
    event_id: UUID = Field(default_factory=uuid4)
    schema_version: int = Field(default=1)
    
    reconciliation_id: UUID
    execution_id: UUID
    request_id: UUID
    
    tenant_id: str
    agent_id: str
    
    reconciliation_result: str
    resulting_status: str
    
    occurred_at: datetime

class IncidentCreatedEvent(BaseModel):
    """
    Emitted when a new Incident is detected.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    event_type: Literal["security.incident.created"] = Field(default="security.incident.created")
    event_id: UUID = Field(default_factory=uuid4)
    schema_version: int = Field(default=1)
    
    incident_id: str
    tenant_id: str
    agent_id: str | None = None
    severity: str
    detection_rule_id: str
    title: str
    
    occurred_at: datetime


def deserialize_event(payload: str) -> BaseModel:
    """
    Deserializes a JSON string back into an Event based on event_type.
    """
    payload_dict = json.loads(payload)
    event_type = payload_dict.get("event_type")
    
    if event_type == "authorization.decision":
        return AuthorizationDecisionEvent.model_validate(payload_dict)
    elif event_type == "action.execution":
        return ActionExecutionEvent.model_validate(payload_dict)
    elif event_type == "action.execution.reconciled":
        return ActionReconciliationEvent.model_validate(payload_dict)
    elif event_type == "security.incident.created":
        return IncidentCreatedEvent.model_validate(payload_dict)
        
    # Fallback to base or dict for others (or raise)
    return payload_dict
