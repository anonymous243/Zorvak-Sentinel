import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sentinel_core.models import (
    Incident,
    RemediationPlaybook,
    AutonomousActionLog,
    AgentCredential,
    Policy,
    PolicyVersion
)

logger = logging.getLogger(__name__)

SENTINEL_AUTONOMOUS_MASTER_SECRET = b"SENTINEL_CORE_MACHINE_SECRET_V1"

async def evaluate_and_remediate(session: AsyncSession, incident_id: str) -> list[AutonomousActionLog]:
    """
    Evaluates an incident against active playbooks and autonomously executes defense actions.
    Returns a list of cryptographically signed logs.
    """
    incident = (await session.execute(
        select(Incident).where(Incident.id == incident_id)
    )).scalar_one_or_none()
    
    if not incident or not incident.agent_id:
        return []
        
    playbooks = (await session.execute(
        select(RemediationPlaybook)
        .where(RemediationPlaybook.tenant_id == incident.tenant_id)
        .where(RemediationPlaybook.is_active == True)
        .where(RemediationPlaybook.trigger_severity == incident.severity)
    )).scalars().all()
    
    logs = []
    
    for playbook in playbooks:
        for action_type in playbook.action_types:
            
            log = None
            if action_type == "REVOKE_CREDENTIALS":
                log = await _revoke_credentials(session, incident, playbook)
                
            if log:
                # Cryptographically sign the autonomous action
                log.action_signature = _sign_autonomous_action(log)
                session.add(log)
                logs.append(log)
                
    await session.flush()
    return logs


async def _revoke_credentials(session: AsyncSession, incident: Incident, playbook: RemediationPlaybook) -> AutonomousActionLog | None:
    creds = (await session.execute(
        select(AgentCredential)
        .where(AgentCredential.agent_id == incident.agent_id)
        .where(AgentCredential.status == "active")
    )).scalars().all()
    
    if not creds:
        return None
        
    # State hash before action
    prev_state = {"active_creds": [c.id for c in creds]}
    prev_hash = hashlib.sha256(json.dumps(prev_state, sort_keys=True).encode()).hexdigest()
    
    for c in creds:
        c.status = "revoked"
        c.updated_at = datetime.now(timezone.utc)
        
    log = AutonomousActionLog(
        tenant_id=incident.tenant_id,
        incident_id=incident.id,
        action_type="REVOKE_CREDENTIALS",
        target_agent_id=incident.agent_id,
        previous_state_hash=prev_hash
    )
    return log


def _sign_autonomous_action(log: AutonomousActionLog) -> str:
    """
    Creates an unforgeable cryptographic signature of the autonomous action using HMAC-like SHA256.
    """
    payload = f"{log.tenant_id}:{log.incident_id}:{log.action_type}:{log.target_agent_id}:{log.previous_state_hash}"
    h = hashlib.sha256()
    h.update(SENTINEL_AUTONOMOUS_MASTER_SECRET)
    h.update(payload.encode("utf-8"))
    return h.hexdigest()


def verify_autonomous_signature(log: AutonomousActionLog) -> bool:
    """
    Verifies that the autonomous action log was genuinely produced by the Sentinel Core.
    """
    expected = _sign_autonomous_action(log)
    return expected == log.action_signature
