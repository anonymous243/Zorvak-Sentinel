import json
import hashlib
from typing import Sequence
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exc

from sentinel_core.models import (
    Evidence, SecurityEvent, Incident, Alert, 
    AuthorizationDecisionRecord, ExecutionRecord, OutboxEvent
)
from sentinel_core.schemas import EvidenceType
from sentinel_core.security_event_service import sanitize_metadata
from sentinel_core.events import EvidenceCreatedEvent

async def create_evidence(
    session: AsyncSession,
    tenant_id: str,
    evidence_type: str,
    source_type: str,
    source_id: str,
    description: str,
    captured_at: datetime,
    incident_id: str | None = None,
    alert_id: str | None = None,
    metadata_payload: dict | None = None,
) -> Evidence:
    """
    Core function to create Evidence, applying sanitization and integrity digests.
    Enforces idempotency using race-recovery patterns.
    """
    # Sanitize and hash metadata
    payload_json = None
    integrity_digest = None
    if metadata_payload:
        sanitized = sanitize_metadata(metadata_payload)
        payload_json = json.dumps(sanitized, ensure_ascii=True, separators=(',', ':'), sort_keys=True)
        # Create deterministic hash for canonical representation
        integrity_digest = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()

    async with session.begin_nested():
        try:
            evidence = Evidence(
                tenant_id=tenant_id,
                incident_id=incident_id,
                alert_id=alert_id,
                evidence_type=evidence_type,
                source_type=source_type,
                source_id=source_id,
                description=description,
                metadata_payload=payload_json,
                integrity_digest=integrity_digest,
                captured_at=captured_at,
            )
            session.add(evidence)
            await session.flush()
            
            # Emit outbox event
            ev_event = EvidenceCreatedEvent(
                evidence_id=evidence.id,
                tenant_id=tenant_id,
                incident_id=incident_id,
                evidence_type=evidence_type,
                source_type=source_type,
                source_id=source_id,
                captured_at=captured_at
            )
            outbox = OutboxEvent(
                aggregate_type="Evidence",
                aggregate_id=evidence.id,
                event_type=ev_event.event_type,
                payload=ev_event.model_dump_json(),
                occurred_at=captured_at
            )
            session.add(outbox)
            return evidence
        except exc.IntegrityError:
            pass
            
    # Race condition lost or already exists, fetch the existing record
    stmt = select(Evidence).where(
        Evidence.tenant_id == tenant_id,
        Evidence.evidence_type == evidence_type,
        Evidence.source_type == source_type,
        Evidence.source_id == source_id,
        Evidence.incident_id == incident_id
    )
    result = await session.execute(stmt)
    existing = result.scalars().first()
    if existing:
        return existing
    raise RuntimeError("Failed to create or retrieve Evidence due to unexpected state.")

async def create_evidence_from_security_event(
    session: AsyncSession, 
    event: SecurityEvent, 
    incident_id: str | None = None
) -> Evidence:
    payload = None
    if event.metadata_payload:
        try:
            payload = json.loads(event.metadata_payload)
        except Exception:
            pass

    return await create_evidence(
        session=session,
        tenant_id=event.tenant_id,
        evidence_type=EvidenceType.SECURITY_EVENT,
        source_type="security_event",
        source_id=event.id,
        description=f"Security Event: {event.event_type}",
        captured_at=event.occurred_at,
        incident_id=incident_id,
        metadata_payload=payload
    )

async def create_evidence_from_incident(
    session: AsyncSession, 
    incident: Incident
) -> Evidence:
    return await create_evidence(
        session=session,
        tenant_id=incident.tenant_id,
        evidence_type=EvidenceType.INCIDENT,
        source_type="incident",
        source_id=incident.id,
        description=f"Incident: {incident.title}",
        captured_at=incident.created_at,
        incident_id=incident.id
    )

async def create_evidence_from_alert(
    session: AsyncSession, 
    alert: Alert
) -> Evidence:
    return await create_evidence(
        session=session,
        tenant_id=alert.tenant_id,
        evidence_type=EvidenceType.ALERT,
        source_type="alert",
        source_id=alert.id,
        description=f"Alert: {alert.title}",
        captured_at=alert.created_at,
        incident_id=alert.incident_id,
        alert_id=alert.id
    )

async def create_evidence_from_decision(
    session: AsyncSession, 
    decision: AuthorizationDecisionRecord,
    incident_id: str | None = None
) -> Evidence:
    payload = {
        "status": decision.status,
        "policy_id": decision.policy_id,
        "policy_version_id": decision.policy_version_id,
        "risk_level": decision.risk_level,
        "action": decision.action,
        "resource": decision.resource
    }
    return await create_evidence(
        session=session,
        tenant_id=decision.tenant_id,
        evidence_type=EvidenceType.DECISION,
        source_type="authorization_decision",
        source_id=decision.id,
        description=f"Authorization Decision: {decision.status}",
        captured_at=decision.created_at,
        incident_id=incident_id,
        metadata_payload=payload
    )

async def create_evidence_from_execution(
    session: AsyncSession, 
    execution: ExecutionRecord,
    incident_id: str | None = None
) -> Evidence:
    payload = {
        "status": execution.status,
        "decision_id": execution.decision_id
    }
    return await create_evidence(
        session=session,
        tenant_id=execution.tenant_id,
        evidence_type=EvidenceType.EXECUTION,
        source_type="execution_record",
        source_id=execution.id,
        description=f"Execution Record: {execution.status}",
        captured_at=execution.execution_time,
        incident_id=incident_id,
        metadata_payload=payload
    )

async def get_evidence(session: AsyncSession, tenant_id: str, evidence_id: str) -> Evidence | None:
    stmt = select(Evidence).where(
        Evidence.id == evidence_id,
        Evidence.tenant_id == tenant_id
    )
    result = await session.execute(stmt)
    return result.scalars().first()

async def list_evidence(
    session: AsyncSession, 
    tenant_id: str,
    incident_id: str | None = None,
    evidence_type: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> Sequence[Evidence]:
    stmt = select(Evidence).where(Evidence.tenant_id == tenant_id)
    if incident_id:
        stmt = stmt.where(Evidence.incident_id == incident_id)
    if evidence_type:
        stmt = stmt.where(Evidence.evidence_type == evidence_type)
        
    stmt = stmt.order_by(Evidence.captured_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()
