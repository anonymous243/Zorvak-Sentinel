from datetime import datetime, timezone
from enum import StrEnum
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskEvaluationStatus(StrEnum):
    SUCCESS = "success"
    UNKNOWN = "unknown"
    ERROR = "error"

class RiskFactor(StrEnum):
    SENSITIVE_ACTION = "sensitive_action"
    SENSITIVE_RESOURCE = "sensitive_resource"
    BEHAVIORAL_DEVIATION = "behavioral_deviation"
    ANOMALOUS_CONTEXT = "anomalous_context"

class RiskAssessment(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    agent_id: str
    request_id: UUID
    credential_id: str

    score: int = Field(ge=0, le=100)
    level: RiskLevel
    factors: List[RiskFactor] = Field(default_factory=list)
    status: RiskEvaluationStatus

    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    evaluation_ms: float = Field(ge=0.0)

class BehaviorSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    factor: RiskFactor
    score_contribution: int

class BehaviorSignalProvider:
    """
    Interface for providing behavioral signals.
    """
    async def get_signals(
        self, tenant_id: str, agent_id: str, action: str, resource: str
    ) -> List[BehaviorSignal]:
        raise NotImplementedError

class DummyBehaviorSignalProvider(BehaviorSignalProvider):
    """
    Dummy provider that returns no signals.
    """
    async def get_signals(
        self, tenant_id: str, agent_id: str, action: str, resource: str
    ) -> List[BehaviorSignal]:
        return []
