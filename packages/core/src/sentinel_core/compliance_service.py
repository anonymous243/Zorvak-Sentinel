from datetime import datetime, timezone
import json
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives import serialization

from sentinel_core.models import EngineNode, CryptographicLease, AutonomousActionLog
from sentinel_core.remediation_service import _sign_autonomous_action

async def generate_compliance_report(session: AsyncSession) -> Dict[str, Any]:
    """
    Scans the database and recalculates cryptographic signatures to prove mathematically
    that the database has not been tampered with.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "scans": {
            "cryptographic_leases": {"total": 0, "verified": 0, "failures": 0},
            "autonomous_actions": {"total": 0, "verified": 0, "failures": 0},
        },
        "failures": []
    }
    
    # 1. Audit Leases
    leases = (await session.execute(select(CryptographicLease))).scalars().all()
    for lease in leases:
        report["scans"]["cryptographic_leases"]["total"] += 1
        
        if not lease.owner_node_id or not lease.cryptographic_proof or not lease.expires_at:
            continue
            
        owner = (await session.execute(
            select(EngineNode).where(EngineNode.id == lease.owner_node_id)
        )).scalar_one_or_none()
        
        if not owner:
            report["status"] = "FAIL"
            report["scans"]["cryptographic_leases"]["failures"] += 1
            report["failures"].append(f"Lease {lease.resource_id} references non-existent node {lease.owner_node_id}")
            continue
            
        try:
            public_key = serialization.load_pem_public_key(owner.public_key.encode("utf-8"))
            expires_at = lease.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            payload = f"{lease.resource_id}:{lease.owner_node_id}:{int(expires_at.timestamp())}".encode("utf-8")
            public_key.verify(bytes.fromhex(lease.cryptographic_proof), payload)
            report["scans"]["cryptographic_leases"]["verified"] += 1
        except Exception as e:
            report["status"] = "FAIL"
            report["scans"]["cryptographic_leases"]["failures"] += 1
            report["failures"].append(f"Lease {lease.resource_id} has a forged signature! {e}")
            
    # 2. Audit Autonomous Actions
    actions = (await session.execute(select(AutonomousActionLog))).scalars().all()
    for action in actions:
        report["scans"]["autonomous_actions"]["total"] += 1
        
        expected_sig = _sign_autonomous_action(action)
        if action.action_signature != expected_sig:
            report["status"] = "FAIL"
            report["scans"]["autonomous_actions"]["failures"] += 1
            report["failures"].append(f"Action {action.id} signature forgery detected!")
        else:
            report["scans"]["autonomous_actions"]["verified"] += 1
            
    return report

