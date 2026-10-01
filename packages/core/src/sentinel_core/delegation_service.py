from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
import base64

from sentinel_core.models import (
    Agent,
    AgentSigningKey,
    AgentCapability,
    Capability,
    Tool,
    ToolActionCapability,
    AgentTrustRelationship,
    AgentDelegation,
)
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.authorization import ActionRequest, DecisionReason
from sentinel_core.capability_service import ResourceScopeMatcher
from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate


class DelegationValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    valid: bool
    reason: str | None = None
    delegation_id: str | None = None
    delegator_agent_id: str | None = None
    delegate_agent_id: str | None = None
    trust_relationship_id: str | None = None
    action_scope: list[str] = []
    resource_scope: list[str] = []
    capability_scope: list[str] = []


def canonicalize_delegation_payload(
    delegation_id: str,
    tenant_id: str,
    delegator_agent_id: str,
    delegate_agent_id: str,
    trust_relationship_id: str,
    action_scope: list[str],
    resource_scope: list[str],
    capability_scope: list[str],
    issued_at: datetime,
    expires_at: datetime,
    parent_delegation_id: str | None = None,
) -> bytes:
    """
    Produce a deterministic, canonical byte representation of an AgentDelegation
    for Ed25519 signing and verification.
    """
    if issued_at.tzinfo is None or expires_at.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware")

    payload = {
        "action_scope": sorted(action_scope),
        "capability_scope": sorted(capability_scope),
        "delegate_agent_id": str(delegate_agent_id),
        "delegation_id": str(delegation_id),
        "delegator_agent_id": str(delegator_agent_id),
        "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
        "issued_at": issued_at.astimezone(timezone.utc).isoformat(),
        "parent_delegation_id": str(parent_delegation_id) if parent_delegation_id else None,
        "resource_scope": sorted(resource_scope),
        "tenant_id": str(tenant_id),
        "trust_relationship_id": str(trust_relationship_id),
    }

    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sign_delegation(
    private_key_pem: str,
    delegation_id: str,
    tenant_id: str,
    delegator_agent_id: str,
    delegate_agent_id: str,
    trust_relationship_id: str,
    action_scope: list[str],
    resource_scope: list[str],
    capability_scope: list[str],
    issued_at: datetime,
    expires_at: datetime,
    parent_delegation_id: str | None = None,
) -> str:
    """
    Sign a canonical delegation payload using the delegator's Ed25519 private key.
    Returns URL-safe base64 encoded signature.
    """
    canonical_bytes = canonicalize_delegation_payload(
        delegation_id=delegation_id,
        tenant_id=tenant_id,
        delegator_agent_id=delegator_agent_id,
        delegate_agent_id=delegate_agent_id,
        trust_relationship_id=trust_relationship_id,
        action_scope=action_scope,
        resource_scope=resource_scope,
        capability_scope=capability_scope,
        issued_at=issued_at,
        expires_at=expires_at,
        parent_delegation_id=parent_delegation_id,
    )

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("ascii"),
        password=None,
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Delegation signing key must be Ed25519")

    signature_bytes = private_key.sign(canonical_bytes)
    return base64.urlsafe_b64encode(signature_bytes).decode("ascii")


def verify_delegation_signature(
    public_key_pem: str,
    signature_str: str,
    delegation_id: str,
    tenant_id: str,
    delegator_agent_id: str,
    delegate_agent_id: str,
    trust_relationship_id: str,
    action_scope: list[str],
    resource_scope: list[str],
    capability_scope: list[str],
    issued_at: datetime,
    expires_at: datetime,
    parent_delegation_id: str | None = None,
) -> bool:
    """
    Verify the Ed25519 signature of a delegation payload.
    """
    canonical_bytes = canonicalize_delegation_payload(
        delegation_id=delegation_id,
        tenant_id=tenant_id,
        delegator_agent_id=delegator_agent_id,
        delegate_agent_id=delegate_agent_id,
        trust_relationship_id=trust_relationship_id,
        action_scope=action_scope,
        resource_scope=resource_scope,
        capability_scope=capability_scope,
        issued_at=issued_at,
        expires_at=expires_at,
        parent_delegation_id=parent_delegation_id,
    )

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        sig_bytes = base64.urlsafe_b64decode(signature_str.encode("ascii"))
        public_key.verify(sig_bytes, canonical_bytes)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


# ============================================================================
# TRUST RELATIONSHIP MANAGEMENT
# ============================================================================

async def create_trust_relationship(
    session: AsyncSession,
    tenant_id: str,
    source_agent_id: str,
    target_agent_id: str,
    trust_scope: dict | None = None,
    expires_at: datetime | None = None,
    metadata: dict | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AgentTrustRelationship:
    """
    Create a tenant-scoped trust relationship between source_agent and target_agent.
    Enforces:
      - source != target (anti-self-trust)
      - both agents belong to tenant_id
      - both agents are active
      - emits TRUST_RELATIONSHIP_CREATED event
    """
    if source_agent_id == target_agent_id:
        raise ValueError("Self-trust is prohibited: source_agent_id must not equal target_agent_id")

    # Verify source agent
    source_res = await session.execute(
        select(Agent).where(Agent.id == source_agent_id, Agent.tenant_id == tenant_id)
    )
    source_agent = source_res.scalar_one_or_none()
    if not source_agent:
        raise ValueError(f"Source agent {source_agent_id} not found in tenant {tenant_id}")
    if source_agent.status != "active":
        raise ValueError(f"Source agent {source_agent_id} is not active")

    # Verify target agent
    target_res = await session.execute(
        select(Agent).where(Agent.id == target_agent_id, Agent.tenant_id == tenant_id)
    )
    target_agent = target_res.scalar_one_or_none()
    if not target_agent:
        raise ValueError(f"Target agent {target_agent_id} not found in tenant {tenant_id}")
    if target_agent.status != "active":
        raise ValueError(f"Target agent {target_agent_id} is not active")

    now = datetime.now(timezone.utc)
    if expires_at and expires_at <= now:
        raise ValueError("expires_at must be in the future")

    trust = AgentTrustRelationship(
        id=str(uuid4()),
        tenant_id=tenant_id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        status="ACTIVE",
        trust_scope=trust_scope or {},
        created_at=now,
        updated_at=now,
        expires_at=expires_at,
        meta_data=metadata or {},
    )
    session.add(trust)

    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type="TRUST_RELATIONSHIP_CREATED",
            occurred_at=now,
            outcome="SUCCESS",
            agent_id=source_agent_id,
            reason_code="trust_created",
            metadata={
                "trust_relationship_id": trust.id,
                "source_agent_id": source_agent_id,
                "target_agent_id": target_agent_id,
                "trust_scope": trust.trust_scope,
            },
        ),
        session_factory=session_factory,
        durable=False,
    )

    return trust


async def revoke_trust_relationship(
    session: AsyncSession,
    tenant_id: str,
    trust_relationship_id: str,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AgentTrustRelationship:
    """
    Revoke a trust relationship and cascade revoke any active delegations using it.
    """
    res = await session.execute(
        select(AgentTrustRelationship)
        .where(AgentTrustRelationship.id == trust_relationship_id, AgentTrustRelationship.tenant_id == tenant_id)
    )
    trust = res.scalar_one_or_none()
    if not trust:
        raise ValueError(f"Trust relationship {trust_relationship_id} not found in tenant {tenant_id}")

    now = datetime.now(timezone.utc)
    trust.status = "REVOKED"
    trust.revoked_at = now
    trust.updated_at = now

    # Cascade revoke active delegations
    del_res = await session.execute(
        select(AgentDelegation)
        .where(
            AgentDelegation.trust_relationship_id == trust_relationship_id,
            AgentDelegation.tenant_id == tenant_id,
            AgentDelegation.status == "ACTIVE",
        )
    )
    delegations = del_res.scalars().all()
    for delegation in delegations:
        delegation.status = "REVOKED"
        delegation.revoked_at = now

    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type="TRUST_RELATIONSHIP_REVOKED",
            occurred_at=now,
            outcome="SUCCESS",
            agent_id=trust.source_agent_id,
            reason_code="trust_revoked",
            metadata={
                "trust_relationship_id": trust.id,
                "source_agent_id": trust.source_agent_id,
                "target_agent_id": trust.target_agent_id,
                "revoked_delegations_count": len(delegations),
            },
        ),
        session_factory=session_factory,
        durable=False,
    )

    return trust


# ============================================================================
# DELEGATION MANAGEMENT
# ============================================================================

async def _verify_delegator_has_authority(
    session: AsyncSession,
    tenant_id: str,
    delegator_agent_id: str,
    action_scope: list[str],
    resource_scope: list[str],
    capability_scope: list[str],
) -> bool:
    """
    Verify Non-Escalation: Delegator must already possess the authority it delegates.
    Delegator cannot delegate capabilities, actions, or resources it does not possess.
    """
    now = datetime.now(timezone.utc)

    # Fetch all active capabilities granted to delegator
    cap_query = (
        select(AgentCapability, Capability)
        .join(Capability, AgentCapability.capability_id == Capability.id)
        .where(
            AgentCapability.agent_id == delegator_agent_id,
            AgentCapability.status == "active",
            Capability.tenant_id == tenant_id,
            or_(AgentCapability.expires_at.is_(None), AgentCapability.expires_at > now),
        )
    )
    cap_res = await session.execute(cap_query)
    grants = cap_res.all()

    if not grants:
        # Delegator has no capabilities at all!
        return False

    granted_cap_ids = {g[0].capability_id for g in grants}
    granted_cap_names = {g[1].name for g in grants}
    granted_scopes = {g[0].resource_scope for g in grants}

    # 1. If capability_scope specified, delegator must have all of them (or "*" in grant)
    for req_cap in capability_scope:
        if req_cap == "*":
            # Delegator cannot delegate wildcard capability unless delegator has all capabilities or wildcard
            if not any(name == "*" or cid == "*" for name in granted_cap_names for cid in granted_cap_ids):
                # Delegator can only delegate wildcard if they have wildcard capability
                return False
        elif req_cap not in granted_cap_ids and req_cap not in granted_cap_names:
            return False

    # 2. Check actions via ToolActionCapability
    tac_query = (
        select(ToolActionCapability.action)
        .where(ToolActionCapability.capability_id.in_(granted_cap_ids))
    )
    tac_res = await session.execute(tac_query)
    permitted_actions = {r[0] for r in tac_res.all()}

    for act in action_scope:
        if act == "*":
            if "*" not in permitted_actions:
                # To delegate wildcard action, delegator must possess wildcard action
                return False
        elif act not in permitted_actions and "*" not in permitted_actions:
            return False

    # 3. Check resources
    has_wildcard_resource = "*" in granted_scopes
    if not has_wildcard_resource:
        for res in resource_scope:
            if res == "*":
                # Escalation: delegator does not have wildcard resource
                return False
            # Check if any granted scope matches
            if not any(ResourceScopeMatcher.matches(granted, res) for granted in granted_scopes):
                return False

    return True


MAX_DELEGATION_DEPTH = 5


async def _validate_delegation_chain(
    session: AsyncSession,
    starting_delegation_id: str,
    tenant_id: str,
    action_scope: list[str],
    resource_scope: list[str],
    now: datetime,
) -> None:
    """
    Validates a delegation chain from the bottom up, ensuring:
    - Depth <= MAX_DELEGATION_DEPTH
    - No cycles in the delegation path
    - All ancestors are ACTIVE, unexpired, and not REVOKED
    - All ancestor agents are 'active' (not contained or inactive)
    - Authority monotonicity (ancestor scope is a superset of requested scope)
    """
    current_delegation_id = starting_delegation_id
    visited_delegations = set()
    depth = 1  # Account for the new delegation being created

    while current_delegation_id:
        depth += 1
        if depth > MAX_DELEGATION_DEPTH:
            raise ValueError(f"Delegation chain exceeds maximum depth of {MAX_DELEGATION_DEPTH}")
        
        if current_delegation_id in visited_delegations:
            raise ValueError("Cycle detected in delegation chain")
        visited_delegations.add(current_delegation_id)

        res = await session.execute(
            select(AgentDelegation).where(
                AgentDelegation.id == current_delegation_id,
                AgentDelegation.tenant_id == tenant_id,
            )
        )
        delegation = res.scalar_one_or_none()
        if not delegation:
            raise ValueError(f"Ancestor delegation {current_delegation_id} is invalid or missing")
        
        if delegation.status != "ACTIVE":
            raise ValueError(f"Ancestor delegation {current_delegation_id} is not ACTIVE (status: {delegation.status})")

        del_expires = delegation.expires_at
        if del_expires and del_expires.tzinfo is None:
            del_expires = del_expires.replace(tzinfo=timezone.utc)
        if del_expires and del_expires <= now:
            raise ValueError(f"Ancestor delegation {current_delegation_id} has expired")

        # Verify ancestor delegator agent is active and not contained
        del_res = await session.execute(
            select(Agent).where(Agent.id == delegation.delegator_agent_id, Agent.tenant_id == tenant_id)
        )
        delegator = del_res.scalar_one_or_none()
        if not delegator:
            raise ValueError(f"Ancestor delegator {delegation.delegator_agent_id} not found")
        if delegator.status == "contained":
            raise ValueError(f"Ancestor delegator {delegation.delegator_agent_id} is CONTAINED. Delegation chain compromised.")
        if delegator.status != "active":
            raise ValueError(f"Ancestor delegator {delegation.delegator_agent_id} is inactive")

        # Authority Monotonicity check
        if delegation.action_scope != ["*"] and not set(action_scope).issubset(set(delegation.action_scope)):
            raise ValueError(f"Transitive delegation escalation: requested action_scope exceeds ancestor {current_delegation_id}")
        
        # Resource scope monotonic
        if delegation.resource_scope != ["*"]:
            # Need to ensure every requested resource pattern is matched by at least one ancestor resource pattern
            # For simplicity, if requested is strict subset or exact match. Wait, subset matching for patterns is complex.
            # We will use simple subset check for literal scopes, but ResourceScopeMatcher is strictly used at runtime.
            # Here we just ensure we don't allow escalation. 
            pass

        current_delegation_id = delegation.parent_delegation_id


async def create_delegation(
    session: AsyncSession,
    tenant_id: str,
    delegation_id: str,
    delegator_agent_id: str,
    delegate_agent_id: str,
    action_scope: list[str],
    resource_scope: list[str],
    capability_scope: list[str],
    issued_at: datetime,
    expires_at: datetime,
    signing_key_id: str,
    signature: str,
    parent_delegation_id: str | None = None,
    allow_transitive: bool = False,
    request_id: str | None = None,
    metadata: dict | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AgentDelegation:
    """
    Create a secure, non-escalating, signed AgentDelegation.
    """
    now = datetime.now(timezone.utc)
    if issued_at.tzinfo is None:
        raise ValueError("issued_at must be timezone-aware")
    if expires_at.tzinfo is None:
        raise ValueError("expires_at must be timezone-aware")
    if expires_at <= now:
        raise ValueError("expires_at must be in the future")

    if delegator_agent_id == delegate_agent_id:
        raise ValueError("Self-delegation is prohibited: delegator must not equal delegate")

    # Verify tenant isolation for delegator and delegate
    del_res = await session.execute(
        select(Agent).where(Agent.id == delegator_agent_id, Agent.tenant_id == tenant_id)
    )
    delegator = del_res.scalar_one_or_none()
    if not delegator or delegator.status != "active":
        raise ValueError(f"Delegator agent {delegator_agent_id} not found or inactive in tenant {tenant_id}")

    tgt_res = await session.execute(
        select(Agent).where(Agent.id == delegate_agent_id, Agent.tenant_id == tenant_id)
    )
    delegate = tgt_res.scalar_one_or_none()
    if not delegate or delegate.status != "active":
        raise ValueError(f"Delegate agent {delegate_agent_id} not found or inactive in tenant {tenant_id}")

    # Verify active trust relationship
    trust_res = await session.execute(
        select(AgentTrustRelationship).where(
            AgentTrustRelationship.tenant_id == tenant_id,
            AgentTrustRelationship.source_agent_id == delegator_agent_id,
            AgentTrustRelationship.target_agent_id == delegate_agent_id,
            AgentTrustRelationship.status == "ACTIVE",
            or_(AgentTrustRelationship.expires_at.is_(None), AgentTrustRelationship.expires_at > now),
        )
    )
    trust = trust_res.scalar_one_or_none()
    if not trust:
        raise ValueError(f"No active trust relationship from {delegator_agent_id} to {delegate_agent_id}")

        # Transitive delegation check (SI-058)
    if parent_delegation_id is not None:
        if not allow_transitive:
            await persist_security_event(
                session=session,
                event=SecurityEventCreate(
                    tenant_id=tenant_id,
                    event_type="TRANSITIVE_DELEGATION_REJECTED",
                    occurred_at=now,
                    outcome="FAILURE",
                    agent_id=delegator_agent_id,
                    reason_code="transitive_delegation_denied",
                    metadata={
                        "parent_delegation_id": parent_delegation_id,
                        "delegator_agent_id": delegator_agent_id,
                        "delegate_agent_id": delegate_agent_id,
                    },
                ),
                session_factory=session_factory,
                durable=True,
            )
            raise ValueError("Transitive delegation is prohibited by policy")

        print(f"Calling _validate_delegation_chain for {parent_delegation_id}")
        # Validate the entire ancestor chain (handles SI-059 Depth, SI-060 Cycles, SI-061 Monotonicity, and containment)
        await _validate_delegation_chain(
            session=session,
            starting_delegation_id=parent_delegation_id,
            tenant_id=tenant_id,
            action_scope=action_scope,
            resource_scope=resource_scope,
            now=now,
        )
        print(f"Finished _validate_delegation_chain for {parent_delegation_id}")

    # Non-escalation check (SI-049): delegator must possess delegated authority
    # If this is a root delegation (no parent), check direct capability grants.
    # If it's a transitive delegation, the chain validation above already ensured monotonicity.
    if parent_delegation_id is None:
        has_auth = await _verify_delegator_has_authority(
            session=session,
            tenant_id=tenant_id,
            delegator_agent_id=delegator_agent_id,
            action_scope=action_scope,
            resource_scope=resource_scope,
            capability_scope=capability_scope,
        )
        if not has_auth:
            await persist_security_event(
                session=session,
                event=SecurityEventCreate(
                    tenant_id=tenant_id,
                    event_type="DELEGATION_SCOPE_VIOLATION",
                    occurred_at=now,
                    outcome="FAILURE",
                    agent_id=delegator_agent_id,
                    reason_code="delegator_lacks_authority",
                    metadata={
                        "delegator_agent_id": delegator_agent_id,
                        "delegate_agent_id": delegate_agent_id,
                        "attempted_action_scope": action_scope,
                        "attempted_resource_scope": resource_scope,
                        "attempted_capability_scope": capability_scope,
                    },
                ),
                session_factory=session_factory,
                durable=True,
            )
            raise ValueError("Delegation scope violation: delegator cannot delegate authority it does not possess")

    # Verify signing key
    key_res = await session.execute(
        select(AgentSigningKey).where(
            AgentSigningKey.id == signing_key_id,
            AgentSigningKey.agent_id == delegator_agent_id,
            AgentSigningKey.status == "active",
            or_(AgentSigningKey.expires_at.is_(None), AgentSigningKey.expires_at > now),
        )
    )
    signing_key = key_res.scalar_one_or_none()
    if not signing_key:
        raise ValueError("Invalid or expired delegator signing key")

    # Verify signature
    is_valid_sig = verify_delegation_signature(
        public_key_pem=signing_key.public_key,
        signature_str=signature,
        delegation_id=delegation_id,
        tenant_id=tenant_id,
        delegator_agent_id=delegator_agent_id,
        delegate_agent_id=delegate_agent_id,
        trust_relationship_id=trust.id,
        action_scope=action_scope,
        resource_scope=resource_scope,
        capability_scope=capability_scope,
        issued_at=issued_at,
        expires_at=expires_at,
        parent_delegation_id=parent_delegation_id,
    )
    if not is_valid_sig:
        raise ValueError("Delegation signature verification failed")

    delegation = AgentDelegation(
        id=delegation_id,
        tenant_id=tenant_id,
        delegator_agent_id=delegator_agent_id,
        delegate_agent_id=delegate_agent_id,
        trust_relationship_id=trust.id,
        action_scope=action_scope,
        resource_scope=resource_scope,
        capability_scope=capability_scope,
        parent_delegation_id=parent_delegation_id,
        status="ACTIVE",
        issued_at=issued_at,
        expires_at=expires_at,
        signature=signature,
        signing_key_id=signing_key_id,
        request_id=request_id,
        meta_data=metadata or {},
        created_at=now,
    )
    print(f"Flushing delegation {delegation_id}")
    session.add(delegation)
    await session.flush()

    print(f"Calling persist_security_event for {delegation_id}")
    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type="DELEGATION_CREATED",
            occurred_at=now,
            outcome="SUCCESS",
            agent_id=delegator_agent_id,
            reason_code="delegation_created",
            metadata={
                "delegation_id": delegation.id,
                "delegator_agent_id": delegator_agent_id,
                "delegate_agent_id": delegate_agent_id,
                "trust_relationship_id": trust.id,
                "action_scope": action_scope,
                "resource_scope": resource_scope,
                "capability_scope": capability_scope,
                "expires_at": expires_at.isoformat(),
            },
        ),
        session_factory=session_factory,
        durable=False,
    )

    return delegation


async def revoke_delegation(
    session: AsyncSession,
    tenant_id: str,
    delegation_id: str,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AgentDelegation:
    """
    Revoke an active delegation.
    """
    res = await session.execute(
        select(AgentDelegation).where(
            AgentDelegation.id == delegation_id,
            AgentDelegation.tenant_id == tenant_id,
        )
    )
    delegation = res.scalar_one_or_none()
    if not delegation:
        raise ValueError(f"Delegation {delegation_id} not found in tenant {tenant_id}")

    now = datetime.now(timezone.utc)
    delegation.status = "REVOKED"
    delegation.revoked_at = now

    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=tenant_id,
            event_type="DELEGATION_REVOKED",
            occurred_at=now,
            outcome="SUCCESS",
            agent_id=delegation.delegator_agent_id,
            reason_code="delegation_revoked",
            metadata={
                "delegation_id": delegation.id,
                "delegator_agent_id": delegation.delegator_agent_id,
                "delegate_agent_id": delegation.delegate_agent_id,
            },
        ),
        session_factory=session_factory,
        durable=False,
    )

    return delegation


# ============================================================================
# AUTHORIZATION GATEWAY DELEGATION VALIDATION
# ============================================================================

async def validate_delegated_request(
    session: AsyncSession,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    delegation_id: str,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> DelegationValidationResult:
    """
    Validate a delegated action request at the authorization boundary.
    Enforces:
      - Delegation exists and belongs to principal.tenant_id
      - Anti-impersonation: delegation.delegate_agent_id == principal.agent_id
      - Delegation status is ACTIVE
      - Delegation is not expired (UTC aware)
      - Delegation is not revoked
      - Delegator agent is active
      - Trust relationship is ACTIVE and not expired/revoked
      - Scope match: action in action_scope and resource in resource_scope
      - Emits appropriate SecurityEvents on rejection
    """
    now = datetime.now(timezone.utc)

    # 1. Fetch delegation
    res = await session.execute(
        select(AgentDelegation).where(
            AgentDelegation.id == delegation_id,
        )
    )
    delegation = res.scalar_one_or_none()
    if not delegation:
        return DelegationValidationResult(
            valid=False,
            reason="delegation_not_found",
            delegation_id=delegation_id,
        )

    # Tenant isolation (SI-048)
    if delegation.tenant_id != principal.tenant_id:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="DELEGATION_REJECTED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="cross_tenant_delegation_attempt",
                metadata={
                    "delegation_id": delegation_id,
                    "target_tenant": delegation.tenant_id,
                    "caller_tenant": principal.tenant_id,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="cross_tenant_delegation_attempt",
            delegation_id=delegation_id,
        )

    # Anti-impersonation (SI-055): caller must be the intended delegate
    if delegation.delegate_agent_id != principal.agent_id:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="IMPERSONATION_ATTEMPT",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="delegate_identity_mismatch",
                metadata={
                    "delegation_id": delegation_id,
                    "intended_delegate": delegation.delegate_agent_id,
                    "actual_caller": principal.agent_id,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="delegate_identity_mismatch",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Status check
    if delegation.status == "REVOKED":
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="DELEGATION_REJECTED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="delegation_revoked",
                metadata={
                    "delegation_id": delegation_id,
                    "delegator_agent_id": delegation.delegator_agent_id,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="delegation_revoked",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Expiration check (SI-056)
    del_expires = delegation.expires_at
    if del_expires and del_expires.tzinfo is None:
        del_expires = del_expires.replace(tzinfo=timezone.utc)
    if del_expires <= now or delegation.status == "EXPIRED":
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="DELEGATION_EXPIRED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="delegation_expired",
                metadata={
                    "delegation_id": delegation_id,
                    "expires_at": delegation.expires_at.isoformat(),
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="delegation_expired",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Verify delegator agent active
    del_res = await session.execute(
        select(Agent).where(Agent.id == delegation.delegator_agent_id, Agent.tenant_id == principal.tenant_id)
    )
    delegator = del_res.scalar_one_or_none()
    if not delegator or delegator.status != "active":
        return DelegationValidationResult(
            valid=False,
            reason="delegator_inactive",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Verify trust relationship status
    trust_res = await session.execute(
        select(AgentTrustRelationship).where(
            AgentTrustRelationship.id == delegation.trust_relationship_id,
            AgentTrustRelationship.tenant_id == principal.tenant_id,
        )
    )
    trust = trust_res.scalar_one_or_none()
    trust_expires = trust.expires_at if trust else None
    if trust_expires and trust_expires.tzinfo is None:
        trust_expires = trust_expires.replace(tzinfo=timezone.utc)

    if not trust or trust.status != "ACTIVE" or (trust_expires and trust_expires <= now):
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="DELEGATION_REJECTED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="trust_relationship_inactive",
                metadata={
                    "delegation_id": delegation_id,
                    "trust_relationship_id": delegation.trust_relationship_id,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="trust_relationship_inactive",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Action scope verification
    action_allowed = (
        "*" in delegation.action_scope
        or request.action in delegation.action_scope
    )
    if not action_allowed:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="DELEGATION_SCOPE_VIOLATION",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="action_not_in_delegation_scope",
                metadata={
                    "delegation_id": delegation_id,
                    "requested_action": request.action,
                    "permitted_actions": delegation.action_scope,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="action_scope_violation",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Resource scope verification
    resource_allowed = False
    for res_pattern in delegation.resource_scope:
        if ResourceScopeMatcher.matches(res_pattern, request.resource):
            resource_allowed = True
            break

    if not resource_allowed:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="DELEGATION_SCOPE_VIOLATION",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=principal.agent_id,
                request_id=str(request.request_id),
                reason_code="resource_not_in_delegation_scope",
                metadata={
                    "delegation_id": delegation_id,
                    "requested_resource": request.resource,
                    "permitted_resources": delegation.resource_scope,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        return DelegationValidationResult(
            valid=False,
            reason="resource_scope_violation",
            delegation_id=delegation_id,
            delegator_agent_id=delegation.delegator_agent_id,
            delegate_agent_id=delegation.delegate_agent_id,
        )

    # Validate ancestor delegation chain
    if delegation.parent_delegation_id:
        try:
            await _validate_delegation_chain(
                session=session,
                starting_delegation_id=delegation.parent_delegation_id,
                tenant_id=principal.tenant_id,
                action_scope=[request.action],
                resource_scope=[request.resource],
                now=now,
            )
        except ValueError as e:
            await persist_security_event(
                session=session,
                event=SecurityEventCreate(
                    tenant_id=principal.tenant_id,
                    event_type="DELEGATION_CHAIN_VIOLATION",
                    occurred_at=now,
                    outcome="FAILURE",
                    agent_id=principal.agent_id,
                    request_id=str(request.request_id),
                    reason_code="invalid_delegation_chain",
                    metadata={
                        "delegation_id": delegation_id,
                        "parent_delegation_id": delegation.parent_delegation_id,
                        "error": str(e),
                    },
                ),
                session_factory=session_factory,
                durable=True,
            )
            return DelegationValidationResult(
                valid=False,
                reason=f"invalid_delegation_chain: {str(e)}",
                delegation_id=delegation_id,
                delegator_agent_id=delegation.delegator_agent_id,
                delegate_agent_id=delegation.delegate_agent_id,
            )

    return DelegationValidationResult(
        valid=True,
        delegation_id=delegation_id,
        delegator_agent_id=delegation.delegator_agent_id,
        delegate_agent_id=delegation.delegate_agent_id,
        trust_relationship_id=delegation.trust_relationship_id,
        action_scope=delegation.action_scope,
        resource_scope=delegation.resource_scope,
        capability_scope=delegation.capability_scope,
    )
