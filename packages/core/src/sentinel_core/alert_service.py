import logging
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from sentinel_core.models import Incident, Alert, AlertAuditRecord
from sentinel_core import outbox_service
from sentinel_core.events import (
    AlertCreatedEvent,
    AlertAcknowledgedEvent,
    AlertResolvedEvent,
    serialize_event
)

logger = logging.getLogger(__name__)


async def create_alert_from_incident(
    session: AsyncSession,
    incident: Incident
) -> Optional[Alert]:
    """
    Idempotently creates a new OPEN alert for an incident.
    Uses the same race-recovery pattern as incident detection to guarantee
    only one OPEN alert per incident.
    """
    now = datetime.now(timezone.utc)
    alert_id = str(uuid4())

    try:
        # Use a SAVEPOINT to isolate the alert creation race
        async with session.begin_nested():
            alert = Alert(
                id=alert_id,
                tenant_id=incident.tenant_id,
                incident_id=incident.id,
                status="OPEN",
                severity=incident.severity,
                title=f"Alert: {incident.title}",
                description=incident.description,
                created_at=now,
                updated_at=now,
            )
            session.add(alert)

            audit = AlertAuditRecord(
                id=str(uuid4()),
                alert_id=alert_id,
                tenant_id=incident.tenant_id,
                operation="CREATED",
                actor_id="system",
                occurred_at=now,
            )
            session.add(audit)

            # Publish outbox event
            evt = AlertCreatedEvent(
                alert_id=alert_id,
                tenant_id=incident.tenant_id,
                incident_id=incident.id,
                status="OPEN",
                occurred_at=now,
            )
            await outbox_service.create_event(
                session=session,
                event_type=evt.event_type,
                aggregate_type="alert",
                aggregate_id=alert_id,
                payload=serialize_event(evt),
                occurred_at=now,
            )

            await session.flush()
        
        logger.info("Alert created for incident=%s alert=%s", incident.id, alert_id)
        return alert

    except IntegrityError:
        # DB blocked it because an OPEN alert already exists for this incident
        logger.info("Concurrent alert creation suppressed for incident=%s", incident.id)
        
        try:
            # Re-fetch from current session (works for SQLite + same-session recovery)
            existing = await _fetch_open_alert_for_incident(session, incident.tenant_id, incident.id)
            if existing:
                return existing
        except Exception as e:
            logger.warning("Re-fetch existing alert failed: %s", e)

        return None

async def _fetch_open_alert_for_incident(
    session: AsyncSession,
    tenant_id: str,
    incident_id: str
) -> Optional[Alert]:
    stmt = select(Alert).where(
        Alert.tenant_id == tenant_id,
        Alert.incident_id == incident_id,
        Alert.status == "OPEN"
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_alert(
    session: AsyncSession,
    tenant_id: str,
    alert_id: str
) -> Optional[Alert]:
    """Retrieves an alert strictly bound by tenant_id."""
    stmt = select(Alert).where(
        Alert.tenant_id == tenant_id,
        Alert.id == alert_id
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def list_alerts(
    session: AsyncSession,
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Sequence[Alert]:
    """Lists alerts strictly bound by tenant_id."""
    stmt = select(Alert).where(Alert.tenant_id == tenant_id)
    
    if status:
        stmt = stmt.where(Alert.status == status)
        
    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def acknowledge_alert(
    session: AsyncSession,
    tenant_id: str,
    alert_id: str,
    actor_id: str
) -> Alert:
    """Transitions an alert from OPEN -> ACKNOWLEDGED."""
    alert = await get_alert(session, tenant_id, alert_id)
    if not alert:
        raise ValueError("Alert not found")
        
    if alert.status != "OPEN":
        raise ValueError(f"Invalid transition from {alert.status} to ACKNOWLEDGED")

    now = datetime.now(timezone.utc)
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = now
    alert.acknowledged_by = actor_id
    alert.updated_at = now

    # Audit record
    audit = AlertAuditRecord(
        id=str(uuid4()),
        alert_id=alert.id,
        tenant_id=tenant_id,
        operation="ACKNOWLEDGED",
        actor_id=actor_id,
        occurred_at=now,
    )
    session.add(audit)
    
    # Outbox event
    evt = AlertAcknowledgedEvent(
        alert_id=alert.id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        occurred_at=now,
    )
    await outbox_service.create_event(
        session=session,
        event_type=evt.event_type,
        aggregate_type="alert",
        aggregate_id=alert.id,
        payload=serialize_event(evt),
        occurred_at=now,
    )

    await session.flush()
    return alert


async def resolve_alert(
    session: AsyncSession,
    tenant_id: str,
    alert_id: str,
    actor_id: str
) -> Alert:
    """Transitions an alert from OPEN|ACKNOWLEDGED -> RESOLVED."""
    alert = await get_alert(session, tenant_id, alert_id)
    if not alert:
        raise ValueError("Alert not found")
        
    if alert.status not in ("OPEN", "ACKNOWLEDGED"):
        raise ValueError(f"Invalid transition from {alert.status} to RESOLVED")

    now = datetime.now(timezone.utc)
    alert.status = "RESOLVED"
    alert.resolved_at = now
    alert.resolved_by = actor_id
    alert.updated_at = now

    # Audit record
    audit = AlertAuditRecord(
        id=str(uuid4()),
        alert_id=alert.id,
        tenant_id=tenant_id,
        operation="RESOLVED",
        actor_id=actor_id,
        occurred_at=now,
    )
    session.add(audit)
    
    # Outbox event
    evt = AlertResolvedEvent(
        alert_id=alert.id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        occurred_at=now,
    )
    await outbox_service.create_event(
        session=session,
        event_type=evt.event_type,
        aggregate_type="alert",
        aggregate_id=alert.id,
        payload=serialize_event(evt),
        occurred_at=now,
    )

    await session.flush()
    return alert
