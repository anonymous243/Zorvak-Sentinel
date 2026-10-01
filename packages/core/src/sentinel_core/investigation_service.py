import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from sentinel_core.models import (
    Investigation, EvidenceLedgerRecord, Incident, SecurityEvent, 
    InvestigationNote, InvestigationFinding, InvestigationAuditRecord,
    OutboxEvent, Alert
)
from sqlalchemy.exc import IntegrityError
from sentinel_core.security_event_service import sanitize_metadata
logger = logging.getLogger(__name__)

class ForensicIntegrityError(Exception):
    pass

def _compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def _canonicalize_dict(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

async def create_investigation(
    session: AsyncSession,
    tenant_id: str,
    incident_id: str,
    title: str,
    actor_id: str,
    summary: str | None = None,
    severity: str = "MEDIUM",
    alert_id: str | None = None,
    assigned_to: str | None = None
) -> Investigation:
    try:
        async with session.begin_nested():
            investigation = Investigation(
                id=str(uuid4()),
                tenant_id=tenant_id,
                incident_id=incident_id,
                alert_id=alert_id,
                status="OPEN",
                severity=severity,
                title=title,
                summary=summary,
                assigned_to=assigned_to,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(investigation)
            
            audit = InvestigationAuditRecord(
                id=str(uuid4()),
                investigation_id=investigation.id,
                tenant_id=tenant_id,
                operation="CREATE",
                actor_id=actor_id,
                occurred_at=datetime.now(timezone.utc)
            )
            session.add(audit)
            
            outbox = OutboxEvent(
                id=str(uuid4()),
                event_type="security.investigation.created",
                aggregate_type="INVESTIGATION",
                aggregate_id=investigation.id,
                payload=json.dumps({
                    "investigation_id": investigation.id,
                    "incident_id": incident_id,
                    "status": "OPEN"
                }),
                occurred_at=datetime.now(timezone.utc)
            )
            session.add(outbox)
            await session.flush()
            
    except IntegrityError as e:
        if "uix_investigations_incident_active" in str(e) or "investigations.incident_id" in str(e):
            raise ValueError(f"An active investigation already exists for incident {incident_id}")
        raise

    return investigation

async def get_investigation(session: AsyncSession, tenant_id: str, investigation_id: str) -> Investigation | None:
    stmt = select(Investigation).where(
        Investigation.id == investigation_id,
        Investigation.tenant_id == tenant_id
    )
    result = await session.execute(stmt)
    return result.scalars().first()

async def attach_evidence(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str,
    entity_type: str,
    entity_id: str,
    added_by: str
) -> EvidenceLedgerRecord:
    # 1. Fetch the investigation and lock it (or at least fetch it)
    investigation = await get_investigation(session, tenant_id, investigation_id)
    if not investigation:
        raise ValueError("Investigation not found or belongs to another tenant")

    # 2. Fetch the entity to ensure it belongs to the tenant and exists
    entity_snapshot_dict = {}
    if entity_type == "INCIDENT":
        stmt = select(Incident).where(Incident.id == entity_id, Incident.tenant_id == tenant_id)
        result = await session.execute(stmt)
        incident = result.scalars().first()
        if not incident:
            raise ValueError(f"Incident {entity_id} not found for tenant {tenant_id}")
        entity_snapshot_dict = {
            "id": incident.id,
            "status": incident.status,
            "severity": incident.severity,
            "detection_rule_id": incident.detection_rule_id,
            "created_at": incident.created_at.isoformat() if incident.created_at else None
        }
    elif entity_type == "SECURITY_EVENT":
        stmt = select(SecurityEvent).where(SecurityEvent.id == entity_id, SecurityEvent.tenant_id == tenant_id)
        result = await session.execute(stmt)
        event = result.scalars().first()
        if not event:
            raise ValueError(f"SecurityEvent {entity_id} not found for tenant {tenant_id}")
        entity_snapshot_dict = {
            "id": event.id,
            "event_type": event.event_type,
            "outcome": event.outcome,
            "agent_id": event.agent_id,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None
        }
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    entity_snapshot_hash = _compute_sha256(_canonicalize_dict(entity_snapshot_dict))

    # 3. Determine the next sequence number and previous hash
    stmt = select(EvidenceLedgerRecord).where(
        EvidenceLedgerRecord.investigation_id == investigation_id
    ).order_by(EvidenceLedgerRecord.seq_num.desc()).limit(1)
    result = await session.execute(stmt)
    last_record = result.scalars().first()

    if last_record:
        seq_num = last_record.seq_num + 1
        previous_hash = last_record.record_hash
    else:
        seq_num = 0
        previous_hash = None

    # 4. Compute the record hash
    # Hash structure: investigation_id + seq_num + (previous_hash or "") + entity_id + entity_snapshot_hash
    hash_input = f"{investigation_id}:{seq_num}:{previous_hash or ''}:{entity_id}:{entity_snapshot_hash}"
    record_hash = _compute_sha256(hash_input)

    # 5. Create the ledger record
    record = EvidenceLedgerRecord(
        id=str(uuid4()),
        investigation_id=investigation_id,
        tenant_id=tenant_id,
        seq_num=seq_num,
        previous_hash=previous_hash,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_snapshot_hash=entity_snapshot_hash,
        record_hash=record_hash,
        added_by=added_by,
        added_at=datetime.now(timezone.utc)
    )
    
    session.add(record)
    
    # 6. Update the investigation head
    investigation.head_hash = record_hash
    investigation.updated_at = datetime.now(timezone.utc)
    
    await session.flush()
    return record


async def verify_ledger_integrity(session: AsyncSession, tenant_id: str, investigation_id: str) -> bool:
    """
    Verifies that the evidence ledger for an investigation is cryptographically intact.
    Raises ForensicIntegrityError if tampering is detected.
    Returns True if intact.
    """
    investigation = await get_investigation(session, tenant_id, investigation_id)
    if not investigation:
        raise ValueError("Investigation not found")

    stmt = select(EvidenceLedgerRecord).where(
        EvidenceLedgerRecord.investigation_id == investigation_id
    ).order_by(EvidenceLedgerRecord.seq_num.asc())
    
    result = await session.execute(stmt)
    records = list(result.scalars().all())
    
    if not records:
        if investigation.head_hash is not None:
            raise ForensicIntegrityError("Investigation head_hash is set but ledger is empty")
        return True
        
    expected_previous_hash = None
    
    for record in records:
        if record.previous_hash != expected_previous_hash:
            raise ForensicIntegrityError(f"Broken chain link at seq {record.seq_num}: expected previous {expected_previous_hash}, got {record.previous_hash}")
            
        hash_input = f"{investigation_id}:{record.seq_num}:{record.previous_hash or ''}:{record.entity_id}:{record.entity_snapshot_hash}"
        computed_hash = _compute_sha256(hash_input)
        
        if computed_hash != record.record_hash:
            raise ForensicIntegrityError(f"Tampered record at seq {record.seq_num}: computed {computed_hash}, stored {record.record_hash}")
            
        expected_previous_hash = computed_hash
        
    if investigation.head_hash != expected_previous_hash:
        raise ForensicIntegrityError(f"Investigation head_hash mismatch: expected {expected_previous_hash}, got {investigation.head_hash}")
        
    return True

async def transition_investigation(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str,
    status: str,
    actor_id: str,
    reason: str | None = None
) -> Investigation:
    valid_transitions = {
        "OPEN": ["IN_PROGRESS", "CLOSED", "RESOLVED"],
        "IN_PROGRESS": ["CONTAINED", "RESOLVED", "CLOSED"],
        "CONTAINED": ["RESOLVED", "CLOSED", "IN_PROGRESS"],
        "RESOLVED": ["CLOSED", "IN_PROGRESS"],
        "CLOSED": ["OPEN"] # Reopen
    }
    
    investigation = await get_investigation(session, tenant_id, investigation_id)
    if not investigation:
        raise ValueError("Investigation not found")
        
    if status not in valid_transitions.get(investigation.status, []):
        raise ValueError(f"Invalid transition from {investigation.status} to {status}")
        
    investigation.status = status
    now = datetime.now(timezone.utc)
    investigation.updated_at = now
    
    if status == "RESOLVED":
        investigation.resolved_at = now
    elif status == "CLOSED":
        investigation.closed_at = now
        
    if status != "RESOLVED" and investigation.resolved_at:
        investigation.resolved_at = None
    if status != "CLOSED" and investigation.closed_at:
        investigation.closed_at = None
        
    audit = InvestigationAuditRecord(
        id=str(uuid4()),
        investigation_id=investigation.id,
        tenant_id=tenant_id,
        operation=f"STATUS_CHANGE_{status}",
        actor_id=actor_id,
        metadata_payload=json.dumps({"reason": sanitize_metadata({"reason": reason}).get("reason") if reason else None}),
        occurred_at=now
    )
    session.add(audit)
    
    outbox = OutboxEvent(
        id=str(uuid4()),
        event_type="security.investigation.status_changed",
        aggregate_type="INVESTIGATION",
        aggregate_id=investigation.id,
        payload=json.dumps({
            "investigation_id": investigation.id,
            "new_status": status
        }),
        occurred_at=now
    )
    session.add(outbox)
    
    return investigation

async def add_investigation_note(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str,
    content: str,
    author_id: str
) -> InvestigationNote:
    investigation = await get_investigation(session, tenant_id, investigation_id)
    if not investigation:
        raise ValueError("Investigation not found")
        
    safe_content = sanitize_metadata({"content": content})["content"]
    
    note = InvestigationNote(
        id=str(uuid4()),
        investigation_id=investigation.id,
        tenant_id=tenant_id,
        author_id=author_id,
        content=safe_content,
        created_at=datetime.now(timezone.utc)
    )
    session.add(note)
    return note

async def list_investigation_notes(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str
) -> list[InvestigationNote]:
    stmt = select(InvestigationNote).where(
        InvestigationNote.tenant_id == tenant_id,
        InvestigationNote.investigation_id == investigation_id
    ).order_by(InvestigationNote.created_at.asc())
    
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def add_investigation_finding(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str,
    title: str,
    description: str,
    created_by: str,
    severity: str | None = None,
    status: str = "OPEN"
) -> InvestigationFinding:
    investigation = await get_investigation(session, tenant_id, investigation_id)
    if not investigation:
        raise ValueError("Investigation not found")
        
    safe_desc = sanitize_metadata({"description": description})["description"]
    
    finding = InvestigationFinding(
        id=str(uuid4()),
        investigation_id=investigation.id,
        tenant_id=tenant_id,
        title=title,
        description=safe_desc,
        severity=severity,
        status=status,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(finding)
    return finding

async def list_investigation_findings(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str
) -> list[InvestigationFinding]:
    stmt = select(InvestigationFinding).where(
        InvestigationFinding.tenant_id == tenant_id,
        InvestigationFinding.investigation_id == investigation_id
    ).order_by(InvestigationFinding.created_at.asc())
    
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_investigation_timeline(
    session: AsyncSession,
    tenant_id: str,
    investigation_id: str
) -> list[dict]:
    # A complete timeline requires merging multiple tables, but since we don't have
    # a unified timeline table, we can fetch notes, findings, audit records, ledger 
    # records, and the incident/alert lifecycle and sort them in-memory.
    investigation = await get_investigation(session, tenant_id, investigation_id)
    if not investigation:
        raise ValueError("Investigation not found")
        
    timeline = []
    
    # Audit records
    audit_stmt = select(InvestigationAuditRecord).where(
        InvestigationAuditRecord.tenant_id == tenant_id,
        InvestigationAuditRecord.investigation_id == investigation_id
    )
    audit_res = await session.execute(audit_stmt)
    for a in audit_res.scalars().all():
        timeline.append({"type": "AUDIT", "occurred_at": a.occurred_at.isoformat(), "operation": a.operation, "actor_id": a.actor_id})
        
    # Notes
    note_stmt = select(InvestigationNote).where(
        InvestigationNote.tenant_id == tenant_id,
        InvestigationNote.investigation_id == investigation_id
    )
    note_res = await session.execute(note_stmt)
    for n in note_res.scalars().all():
        timeline.append({"type": "NOTE", "occurred_at": n.created_at.isoformat(), "author_id": n.author_id, "content": n.content})
        
    # Findings
    finding_stmt = select(InvestigationFinding).where(
        InvestigationFinding.tenant_id == tenant_id,
        InvestigationFinding.investigation_id == investigation_id
    )
    finding_res = await session.execute(finding_stmt)
    for f in finding_res.scalars().all():
        timeline.append({"type": "FINDING_CREATED", "occurred_at": f.created_at.isoformat(), "title": f.title, "status": f.status})
        
    # Ledger
    ledger_stmt = select(EvidenceLedgerRecord).where(
        EvidenceLedgerRecord.tenant_id == tenant_id,
        EvidenceLedgerRecord.investigation_id == investigation_id
    )
    ledger_res = await session.execute(ledger_stmt)
    for l in ledger_res.scalars().all():
        timeline.append({"type": "EVIDENCE_ATTACHED", "occurred_at": l.added_at.isoformat(), "entity_type": l.entity_type, "entity_id": l.entity_id})
        
    timeline.sort(key=lambda x: x["occurred_at"])
    return timeline

