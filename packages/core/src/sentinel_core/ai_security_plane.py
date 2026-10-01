import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from sentinel_core.models import AIAgentAttestation, AIActionVelocityState, AIPendingHighRiskAction, Agent

class AIControlPlaneException(Exception):
    pass


async def _record_attestation_event(
    session: AsyncSession,
    tenant_id: str,
    agent_id: str | None,
    claimed_model_hash: str,
    outcome: str,
    reason: str | None = None,
) -> None:
    from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
    
    event_type = "SOFTWARE_ATTESTATION_VERIFIED" if outcome == "SUCCESS" else "SOFTWARE_ATTESTATION_FAILED"
    
    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            outcome=outcome,
            agent_id=agent_id,
            reason_code=reason,
            metadata={
                "attestation_type": "software_signed",
                "claimed_model_hash": claimed_model_hash,
                "hardware_attestation": False,
            },
        ),
        durable=True,
    )


async def verify_ai_attestation(
    session: AsyncSession,
    tenant_id: str,
    agent_id: str,
    model_hash: str,
    signature_hex: str | None = None,
    public_key_pem: str | None = None,
    tee_signature_hex: str | None = None,
    tee_public_key_pem: str | None = None,
    max_age_seconds: int | None = None,
) -> AIAgentAttestation:
    """
    Verifies Ed25519 software signature over an agent identity and claimed model hash.
    
    Security Boundary:
    - PROVES: Ed25519 signing key control, payload byte integrity, identity binding.
    - DOES NOT PROVE: TEE execution, hardware enclave, secure boot, runtime model memory
      integrity, or actual model execution.
    """
    effective_sig = signature_hex or tee_signature_hex
    effective_key = public_key_pem or tee_public_key_pem

    if not effective_sig or not effective_key:
        await _record_attestation_event(
            session=session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            claimed_model_hash=model_hash,
            outcome="FAILURE",
            reason="missing_signature_or_key",
        )
        raise AIControlPlaneException("Missing signature or public key for software agent attestation.")

    # 1. Tenant & Agent Validation — verify agent belongs to specified tenant
    agent_exists = (await session.execute(
        select(Agent).where(Agent.id == agent_id).where(Agent.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not agent_exists:
        await _record_attestation_event(
            session=session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            claimed_model_hash=model_hash,
            outcome="FAILURE",
            reason="agent_not_found_or_tenant_mismatch",
        )
        raise AIControlPlaneException("Agent not found or belongs to another tenant.")

    # 2. Ed25519 Cryptographic Signature Verification
    try:
        public_key = serialization.load_pem_public_key(effective_key.encode("utf-8"))
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key must be an Ed25519 public key")
        payload = f"{agent_id}:{model_hash}".encode("utf-8")
        public_key.verify(bytes.fromhex(effective_sig), payload)
    except InvalidSignature:
        await _record_attestation_event(
            session=session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            claimed_model_hash=model_hash,
            outcome="FAILURE",
            reason="invalid_signature",
        )
        raise AIControlPlaneException("Invalid software signature. Software agent attestation failed.")
    except Exception as e:
        await _record_attestation_event(
            session=session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            claimed_model_hash=model_hash,
            outcome="FAILURE",
            reason=f"signature_error: {str(e)}",
        )
        raise AIControlPlaneException(f"Error verifying software signature: {str(e)}")

    # 3. Store or Update Attestation Record
    attestation = (await session.execute(
        select(AIAgentAttestation)
        .join(Agent, Agent.id == AIAgentAttestation.agent_id)
        .where(AIAgentAttestation.agent_id == agent_id)
        .where(Agent.tenant_id == tenant_id)
    )).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not attestation:
        attestation = AIAgentAttestation(
            agent_id=agent_id,
            model_hash=model_hash,
            tee_signature=effective_sig,
            verified_at=now,
        )
        session.add(attestation)
    else:
        # Check freshness if max_age_seconds is enforced
        if max_age_seconds is not None:
            db_verified_at = attestation.verified_at
            if db_verified_at.tzinfo is None:
                db_verified_at = db_verified_at.replace(tzinfo=timezone.utc)
            age = (now - db_verified_at).total_seconds()
            if age > max_age_seconds:
                await _record_attestation_event(
                    session=session,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    claimed_model_hash=model_hash,
                    outcome="FAILURE",
                    reason="attestation_stale",
                )
                raise AIControlPlaneException(f"Attestation is stale ({age:.1f}s > {max_age_seconds}s).")

        attestation.model_hash = model_hash
        attestation.tee_signature = effective_sig
        attestation.verified_at = now

    await session.flush()

    # Record successful attestation event
    await _record_attestation_event(
        session=session,
        tenant_id=tenant_id,
        agent_id=agent_id,
        claimed_model_hash=model_hash,
        outcome="SUCCESS",
    )

    return attestation



async def enforce_ai_velocity(session: AsyncSession, tenant_id: str, agent_id: str, max_tokens: float, refill_rate_per_sec: float) -> AIActionVelocityState:
    """
    Enforces velocity limits for AI actions using a Token Bucket algorithm.
    """
    state = (await session.execute(
        select(AIActionVelocityState)
        .join(Agent, Agent.id == AIActionVelocityState.agent_id)
        .where(AIActionVelocityState.agent_id == agent_id)
        .where(Agent.tenant_id == tenant_id)
        .with_for_update()
    )).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not state:
        # Verify agent belongs to tenant
        agent_exists = (await session.execute(
            select(Agent).where(Agent.id == agent_id).where(Agent.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not agent_exists:
            raise AIControlPlaneException("Agent not found or belongs to another tenant.")

        state = AIActionVelocityState(
            agent_id=agent_id,
            tokens=max_tokens,
            last_refill=now,
            locked_out=False
        )
        session.add(state)
        await session.flush()

    if state.locked_out:
        raise AIControlPlaneException("AI Agent is mathematically locked out due to velocity violation.")

    # Calculate tokens to add based on elapsed time
    last_refill = state.last_refill
    if last_refill.tzinfo is None:
        last_refill = last_refill.replace(tzinfo=timezone.utc)
    elapsed = (now - last_refill).total_seconds()
    
    # Handle naive vs aware datetime correctly just in case
    # Since we set now to utc it should be fine
    
    new_tokens = state.tokens + (elapsed * refill_rate_per_sec)
    state.tokens = min(new_tokens, max_tokens)
    state.last_refill = now

    if state.tokens < 1.0:
        state.locked_out = True
        await session.flush()
        
        # Trigger autonomous containment
        await contain_agent(session, tenant_id, agent_id, reason="velocity_threshold_exceeded")
        
        raise AIControlPlaneException("Velocity limit exceeded. AI Agent is now locked out.")

    state.tokens -= 1.0
    await session.flush()
    return state


async def request_high_risk_action(session: AsyncSession, tenant_id: str, agent_id: str, action_payload: dict, required_signatures: int = 2) -> AIPendingHighRiskAction:
    """
    Creates a pending high-risk action requiring M-of-N human signatures.
    """
    if not isinstance(required_signatures, int) or isinstance(required_signatures, bool) or required_signatures < 1:
        raise AIControlPlaneException(
            f"Invalid quorum configuration: required_signatures must be an integer >= 1, got {required_signatures}."
        )

    # Verify agent belongs to tenant
    agent_exists = (await session.execute(
        select(Agent).where(Agent.id == agent_id).where(Agent.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not agent_exists:
        raise AIControlPlaneException("Agent not found or belongs to another tenant.")

    action = AIPendingHighRiskAction(
        agent_id=agent_id,
        action_payload=json.dumps(action_payload),
        required_signatures=required_signatures,
        collected_signatures="[]",
        status="pending"
    )
    session.add(action)
    await session.flush()
    return action


async def submit_human_quorum_signature(session: AsyncSession, tenant_id: str, action_id: str, human_pub_key_pem: str, signature_hex: str) -> AIPendingHighRiskAction:
    """
    Collects a cryptographic signature from a human admin for a pending action.
    """
    action = (await session.execute(
        select(AIPendingHighRiskAction)
        .join(Agent, Agent.id == AIPendingHighRiskAction.agent_id)
        .where(AIPendingHighRiskAction.id == action_id)
        .where(Agent.tenant_id == tenant_id)
        .with_for_update()
    )).scalar_one_or_none()

    if not action:
        raise AIControlPlaneException("Pending action not found.")
    
    if action.status != "pending":
        raise AIControlPlaneException(f"Action is not pending (status: {action.status}).")

    if action.required_signatures is None or action.required_signatures < 1:
        raise AIControlPlaneException(
            f"Invalid quorum configuration: required_signatures must be >= 1, got {action.required_signatures}."
        )

    # Verify signature over the action payload
    try:
        public_key = serialization.load_pem_public_key(human_pub_key_pem.encode("utf-8"))
        payload = action.action_payload.encode("utf-8")
        public_key.verify(bytes.fromhex(signature_hex), payload)
    except InvalidSignature:
        raise AIControlPlaneException("Invalid human signature.")
    except Exception as e:
        raise AIControlPlaneException(f"Error verifying signature: {str(e)}")

    try:
        signatures = json.loads(action.collected_signatures)
        if not isinstance(signatures, list):
            raise ValueError("collected_signatures must be a list")
    except Exception as e:
        raise AIControlPlaneException(f"Corrupted signature data: {str(e)}")
    
    # Prevent duplicate signatures from same key
    if any(s["pub_key"] == human_pub_key_pem for s in signatures):
        raise AIControlPlaneException("Admin has already signed this action.")
        
    sig_entry = {"pub_key": human_pub_key_pem, "signature": signature_hex}
    signatures.append(sig_entry)
    action.collected_signatures = json.dumps(signatures)
    await session.flush()
    return action


async def execute_quorum_action(session: AsyncSession, tenant_id: str, action_id: str) -> dict:
    """
    Executes the action if the required M signatures have been collected.
    """
    action = (await session.execute(
        select(AIPendingHighRiskAction)
        .join(Agent, Agent.id == AIPendingHighRiskAction.agent_id)
        .where(AIPendingHighRiskAction.id == action_id)
        .where(Agent.tenant_id == tenant_id)
        .with_for_update()
    )).scalar_one_or_none()

    if not action:
        raise AIControlPlaneException("Pending action not found.")
        
    if action.status != "pending":
        raise AIControlPlaneException(f"Action is already {action.status}.")

    # F-09: Fail closed on missing, zero, or negative required_signatures
    if action.required_signatures is None or action.required_signatures < 1:
        raise AIControlPlaneException(
            f"Invalid quorum configuration: required_signatures must be >= 1, got {action.required_signatures}."
        )

    try:
        signatures = json.loads(action.collected_signatures)
        if not isinstance(signatures, list):
            raise ValueError("collected_signatures must be a list")
    except Exception as e:
        raise AIControlPlaneException(f"Corrupted signature data: {str(e)}")

    # Distinct signers check to ensure duplicate signatures cannot satisfy quorum
    distinct_signers = set()
    for sig in signatures:
        if not isinstance(sig, dict) or "pub_key" not in sig or "signature" not in sig:
            raise AIControlPlaneException("Corrupted signature entry in collected signatures.")
        distinct_signers.add(sig["pub_key"])

    if len(distinct_signers) < action.required_signatures:
        raise AIControlPlaneException(
            f"Quorum not met. Have {len(distinct_signers)} distinct signature(s), need {action.required_signatures}."
        )

    # Mark as executed
    action.status = "executed"
    await session.flush()
    return json.loads(action.action_payload)

async def disable_agent(session: AsyncSession, tenant_id: str, agent_id: str) -> None:
    """Kill switch: Disable an agent."""
    agent = (await session.execute(
        select(Agent).where(Agent.id == agent_id).where(Agent.tenant_id == tenant_id).with_for_update()
    )).scalar_one_or_none()
    
    if not agent:
        raise AIControlPlaneException("Agent not found.")
        
    if agent.status == "disabled":
        return
        
    previous_status = agent.status
    agent.status = "disabled"
    await session.flush()
    
    from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type="AGENT_KILL_SWITCH_ACTIVATED",
            occurred_at=datetime.now(timezone.utc),
            outcome="SUCCESS",
            agent_id=agent_id,
            metadata={"previous_status": previous_status}
        ),
        durable=True,
    )

async def contain_agent(session: AsyncSession, tenant_id: str, agent_id: str, reason: str) -> None:
    """Autonomous containment: Lock an agent down due to suspicious behavior."""
    agent = (await session.execute(
        select(Agent).where(Agent.id == agent_id).where(Agent.tenant_id == tenant_id).with_for_update()
    )).scalar_one_or_none()
    
    if not agent:
        raise AIControlPlaneException("Agent not found.")
        
    if agent.status in ["contained", "disabled"]:
        return
        
    previous_status = agent.status
    agent.status = "contained"
    await session.flush()
    
    from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type="AGENT_CONTAINED",
            occurred_at=datetime.now(timezone.utc),
            outcome="SUCCESS",
            agent_id=agent_id,
            reason_code=reason,
            metadata={"previous_status": previous_status}
        ),
        durable=True,
    )

