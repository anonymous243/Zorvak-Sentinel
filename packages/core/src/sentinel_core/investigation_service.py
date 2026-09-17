import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from sentinel_core.models import Investigation, EvidenceLedgerRecord, Incident, SecurityEvent

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
    title: str,
    owner_id: str | None = None,
    summary: str | None = None
) -> Investigation:
    investigation = Investigation(
        id=str(uuid4()),
        tenant_id=tenant_id,
        title=title,
        owner_id=owner_id,
        summary=summary,
        status="OPEN",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(investigation)
    await session.flush()
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
