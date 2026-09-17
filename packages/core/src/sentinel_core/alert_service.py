import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sentinel_core.models import Incident, Alert, AlertChannel
from sentinel_core.events import IncidentCreatedEvent
from uuid import uuid4

logger = logging.getLogger(__name__)

async def process_incident_created(
    session: AsyncSession,
    event: IncidentCreatedEvent
) -> list[Alert]:
    """
    Consumes an IncidentCreatedEvent, looks up configured AlertChannels for the tenant,
    and creates Alert records. For Stage 11, we simulate delivery by marking them DELIVERED
    if configuration is valid.
    """
    
    # Fetch active channels for the tenant
    stmt = select(AlertChannel).where(
        AlertChannel.tenant_id == event.tenant_id,
        AlertChannel.status == "active"
    )
    result = await session.execute(stmt)
    channels = result.scalars().all()
    
    alerts = []
    
    for channel in channels:
        # Simulate payload rendering
        payload = {
            "incident_id": event.incident_id,
            "title": event.title,
            "severity": event.severity,
            "rule": event.detection_rule_id,
            "agent_id": event.agent_id
        }
        
        # In a real system, we'd enqueue this to a specific delivery worker.
        # For Stage 11, we represent the lifecycle here.
        alert_status = "DELIVERED"
        if "fail_simulation" in channel.configuration:
            alert_status = "FAILED"
            
        alert = Alert(
            id=str(uuid4()),
            tenant_id=event.tenant_id,
            incident_id=event.incident_id,
            channel_id=channel.id,
            status=alert_status,
            payload=json.dumps(payload),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(alert)
        alerts.append(alert)
        
    await session.flush()
    return alerts
