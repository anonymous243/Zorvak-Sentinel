import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sentinel_core.models import Incident, IncidentAuditRecord, SecurityEvent
from pydantic import BaseModel, ConfigDict
from uuid import uuid4

class IncidentDetectionConfig:
    # 5 denials within 5 minutes triggers an incident
    THRESHOLD_COUNT = 5
    TIME_WINDOW_MINUTES = 5

async def detect_incidents_from_event(
    session: AsyncSession,
    tenant_id: str,
    event_type: str,
    agent_id: str | None,
    occurred_at: datetime
) -> Incident | None:
    """
    Evaluates detection rules inline for a given incoming SecurityEvent.
    If a threshold is crossed, creates a deduplicated Incident.
    """
    
    # 1. Critical Risk Rule
    if event_type == "RISK_CRITICAL":
        return await _create_incident_if_novel(
            session,
            tenant_id,
            agent_id,
            rule_id="RULE_CRITICAL_RISK",
            title="Critical Risk Evaluated",
            description=f"A critical risk evaluation occurred.",
            severity="CRITICAL"
        )
        
    # 2. Repeated Policy Denials
    if event_type == "POLICY_DENIED" and agent_id:
        return await _check_threshold_rule(
            session,
            tenant_id,
            agent_id,
            event_type="POLICY_DENIED",
            rule_id="RULE_REPEATED_POLICY_DENIALS",
            title="Repeated Policy Denials",
            description=f"Agent experienced more than {IncidentDetectionConfig.THRESHOLD_COUNT} policy denials within {IncidentDetectionConfig.TIME_WINDOW_MINUTES} minutes.",
            severity="HIGH"
        )
        
    # 3. Repeated Capability Denials
    if event_type == "CAPABILITY_DENIED" and agent_id:
        return await _check_threshold_rule(
            session,
            tenant_id,
            agent_id,
            event_type="CAPABILITY_DENIED",
            rule_id="RULE_REPEATED_CAPABILITY_DENIALS",
            title="Repeated Capability Denials",
            description=f"Agent experienced more than {IncidentDetectionConfig.THRESHOLD_COUNT} capability denials within {IncidentDetectionConfig.TIME_WINDOW_MINUTES} minutes.",
            severity="HIGH"
        )
        
    return None

async def _check_threshold_rule(
    session: AsyncSession,
    tenant_id: str,
    agent_id: str,
    event_type: str,
    rule_id: str,
    title: str,
    description: str,
    severity: str
) -> Incident | None:
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=IncidentDetectionConfig.TIME_WINDOW_MINUTES)
    
    # Count recent events of this type
    count_stmt = select(func.count()).where(
        SecurityEvent.tenant_id == tenant_id,
        SecurityEvent.agent_id == agent_id,
        SecurityEvent.event_type == event_type,
        SecurityEvent.occurred_at >= cutoff_time
    )
    result = await session.execute(count_stmt)
    count = result.scalar() or 0
    
    if count >= IncidentDetectionConfig.THRESHOLD_COUNT:
        return await _create_incident_if_novel(
            session, tenant_id, agent_id, rule_id, title, description, severity
        )
        
    return None


async def _create_incident_if_novel(
    session: AsyncSession,
    tenant_id: str,
    agent_id: str | None,
    rule_id: str,
    title: str,
    description: str,
    severity: str
) -> Incident | None:
    
    # Deduplication: is there an OPEN incident for this rule + agent?
    check_stmt = select(Incident).where(
        Incident.tenant_id == tenant_id,
        Incident.detection_rule_id == rule_id,
        Incident.status == "OPEN"
    )
    if agent_id:
        check_stmt = check_stmt.where(Incident.agent_id == agent_id)
        
    existing_result = await session.execute(check_stmt)
    existing = existing_result.first()
    
    if existing:
        return None # Suppress duplicate
        
    # Create Incident
    incident_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    incident = Incident(
        id=incident_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        status="OPEN",
        severity=severity,
        detection_rule_id=rule_id,
        title=title,
        description=description,
        created_at=now,
        updated_at=now,
    )
    session.add(incident)
    
    # Audit trail
    audit = IncidentAuditRecord(
        id=str(uuid4()),
        incident_id=incident_id,
        tenant_id=tenant_id,
        operation="CREATED",
        occurred_at=now,
        actor_id="system"
    )
    session.add(audit)
    
    from sentinel_core import outbox_service
    from sentinel_core.events import IncidentCreatedEvent, serialize_event
    
    event = IncidentCreatedEvent(
        incident_id=incident_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        severity=severity,
        detection_rule_id=rule_id,
        title=title,
        occurred_at=now
    )
    
    await outbox_service.create_event(
        session=session,
        event_type=event.event_type,
        aggregate_type="incident",
        aggregate_id=incident_id,
        payload=serialize_event(event),
        occurred_at=now
    )
    
    await session.flush()
    return incident
