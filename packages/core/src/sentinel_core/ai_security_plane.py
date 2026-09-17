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


async def verify_ai_attestation(session: AsyncSession, tenant_id: str, agent_id: str, model_hash: str, tee_signature_hex: str, tee_public_key_pem: str) -> AIAgentAttestation:
    """
    Verifies that the AI Agent's TEE signature is valid for its model hash.
    If valid, stores/updates the attestation.
    """
    try:
        public_key = serialization.load_pem_public_key(tee_public_key_pem.encode("utf-8"))
        payload = f"{agent_id}:{model_hash}".encode("utf-8")
        public_key.verify(bytes.fromhex(tee_signature_hex), payload)
    except InvalidSignature:
        raise AIControlPlaneException("Invalid TEE signature. AI Agent attestation failed.")
    except Exception as e:
        raise AIControlPlaneException(f"Error verifying TEE signature: {str(e)}")

    attestation = (await session.execute(
        select(AIAgentAttestation)
        .join(Agent, Agent.id == AIAgentAttestation.agent_id)
        .where(AIAgentAttestation.agent_id == agent_id)
        .where(Agent.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not attestation:
        # Verify agent belongs to tenant
        agent_exists = (await session.execute(
            select(Agent).where(Agent.id == agent_id).where(Agent.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not agent_exists:
            raise AIControlPlaneException("Agent not found or belongs to another tenant.")

        attestation = AIAgentAttestation(
            agent_id=agent_id,
            model_hash=model_hash,
            tee_signature=tee_signature_hex
        )
        session.add(attestation)
    else:
        attestation.model_hash = model_hash
        attestation.tee_signature = tee_signature_hex
        attestation.verified_at = datetime.now(timezone.utc)

    await session.flush()
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
    elapsed = (now - state.last_refill).total_seconds()
    
    # Handle naive vs aware datetime correctly just in case
    # Since we set now to utc it should be fine
    
    new_tokens = state.tokens + (elapsed * refill_rate_per_sec)
    state.tokens = min(new_tokens, max_tokens)
    state.last_refill = now

    if state.tokens < 1.0:
        state.locked_out = True
        await session.flush()
        raise AIControlPlaneException("Velocity limit exceeded. AI Agent is now locked out.")

    state.tokens -= 1.0
    await session.flush()
    return state


async def request_high_risk_action(session: AsyncSession, tenant_id: str, agent_id: str, action_payload: dict, required_signatures: int = 2) -> AIPendingHighRiskAction:
    """
    Creates a pending high-risk action requiring M-of-N human signatures.
    """
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

    # Verify signature over the action payload
    try:
        public_key = serialization.load_pem_public_key(human_pub_key_pem.encode("utf-8"))
        payload = action.action_payload.encode("utf-8")
        public_key.verify(bytes.fromhex(signature_hex), payload)
    except InvalidSignature:
        raise AIControlPlaneException("Invalid human signature.")
    except Exception as e:
        raise AIControlPlaneException(f"Error verifying signature: {str(e)}")

    signatures = json.loads(action.collected_signatures)
    
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

    signatures = json.loads(action.collected_signatures)
    if len(signatures) < action.required_signatures:
        raise AIControlPlaneException(f"Quorum not met. Have {len(signatures)}, need {action.required_signatures}.")

    # Mark as executed
    action.status = "executed"
    await session.flush()
    return json.loads(action.action_payload)
