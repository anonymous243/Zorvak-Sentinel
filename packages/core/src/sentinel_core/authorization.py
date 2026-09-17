from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DecisionEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class DecisionReason(StrEnum):
    POLICY_ALLOWED = "policy_allowed"
    POLICY_DENIED = "policy_denied"
    NO_MATCHING_POLICY = "no_matching_policy"
    AGENT_NOT_FOUND = "agent_not_found"
    AGENT_DISABLED = "agent_disabled"
    INVALID_REQUEST = "invalid_request"
    EVALUATION_ERROR = "evaluation_error"
    RISK_DENIED = "risk_denied"
    RISK_EVALUATION_ERROR = "risk_evaluation_error"
    CAPABILITY_DENIED = "capability_denied"
    INVALID_POLICY_STATE = "invalid_policy_state"


class ActionRequest(BaseModel):
    """
    Canonical authorization request entering SENTINEL.

    This object is deliberately transport-agnostic. It must remain usable
    from HTTP, SDK, message queues, agent runtimes, and internal services.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    request_id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(min_length=1, max_length=36)
    tool_id: str = Field(min_length=1, max_length=36)
    action: str = Field(min_length=1, max_length=255)
    resource: str = Field(min_length=1, max_length=255)

    # Optional caller-provided context. The authorization engine must never
    # silently treat arbitrary context as trusted identity information.
    context: Mapping[str, str] = Field(default_factory=dict)


class AuthorizationDecision(BaseModel):
    """
    Immutable result of a SENTINEL authorization evaluation.

    A decision is a security event in its own right: it carries enough
    information to correlate the evaluation without requiring callers to
    reconstruct what happened later.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    decision_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    tenant_id: str
    agent_id: str
    credential_id: str
    action: str
    resource: str

    effect: DecisionEffect
    reason: DecisionReason

    policy_id: str | None = None
    policy_version_id: str | None = None
    risk_assessment_id: UUID | None = None
    tool_id: str | None = None
    capability_id: str | None = None

    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    evaluation_ms: float = Field(ge=0.0)

    @property
    def allowed(self) -> bool:
        return self.effect is DecisionEffect.ALLOW
