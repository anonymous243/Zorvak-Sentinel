import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sentinel_core.models import SecurityEvent
from pydantic import BaseModel, ConfigDict, Field
from typing import Mapping, Any, Optional

class SecurityEventCreate(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    tenant_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    occurred_at: datetime
    outcome: str = Field(..., min_length=1)
    
    agent_id: Optional[str] = None
    credential_id: Optional[str] = None
    tool_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version_id: Optional[str] = None
    execution_id: Optional[str] = None
    authorization_decision_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    
    reason_code: Optional[str] = None
    metadata: Optional[Mapping[str, Any]] = None


async def persist_security_event(
    session: AsyncSession,
    event: SecurityEventCreate
) -> SecurityEvent:
    """
    Persists a deterministic security event.
    Must be called within an existing UoW/transaction.
    Does NOT call session.commit() or session.rollback().
    """
    metadata_json = None
    if event.metadata:
        # Sanitize / ensure bounded representation. In a real app we'd strip secrets.
        metadata_json = json.dumps(event.metadata, ensure_ascii=True, separators=(',', ':'))

    db_event = SecurityEvent(
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        outcome=event.outcome,
        agent_id=event.agent_id,
        credential_id=event.credential_id,
        tool_id=event.tool_id,
        policy_id=event.policy_id,
        policy_version_id=event.policy_version_id,
        execution_id=event.execution_id,
        authorization_decision_id=event.authorization_decision_id,
        correlation_id=event.correlation_id,
        request_id=event.request_id,
        reason_code=event.reason_code,
        metadata_payload=metadata_json,
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(db_event)
    await session.flush()
    
    from sentinel_core.incident_detector import detect_incidents_from_event
    await detect_incidents_from_event(
        session=session,
        tenant_id=db_event.tenant_id,
        event_type=db_event.event_type,
        agent_id=db_event.agent_id,
        occurred_at=db_event.occurred_at
    )
    
    return db_event
