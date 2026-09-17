from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from sentinel_core.models import Policy, PolicyVersion, PolicyAuditRecord
from sentinel_core.principals import AuthenticatedPrincipal
import json
from datetime import datetime, timezone
from typing import Any
from sentinel_core.schemas import PolicyCreate, PolicyRollbackResult


from sentinel_core.policy_validator import validate_policy_version



def _deterministic_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

def _snapshot_policy(policy: Policy | None) -> dict[str, Any] | None:
    if not policy:
        return None
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "name": policy.name,
        "enabled": policy.enabled,
        "active_version_id": policy.active_version_id,
    }

def _snapshot_version(version: PolicyVersion | None) -> dict[str, Any] | None:
    if not version:
        return None
    return {
        "id": version.id,
        "policy_id": version.policy_id,
        "tenant_id": version.tenant_id,
        "version": version.version,
        "effect": version.effect,
        "priority": version.priority,
        "action": version.action,
        "resource": version.resource,
        "status": version.status,
    }

def record_policy_audit(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    operation: str,
    policy_id: str,
    policy_version_id: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
):
    audit = PolicyAuditRecord(
        tenant_id=principal.tenant_id,
        agent_id=principal.agent_id,
        credential_id=principal.credential_id,
        policy_id=policy_id,
        policy_version_id=policy_version_id,
        operation=operation,
        before_state=_deterministic_json(before_state) if before_state is not None else None,
        after_state=_deterministic_json(after_state) if after_state is not None else None,
        occurred_at=datetime.now(timezone.utc),
        request_id=request_id,
        correlation_id=correlation_id,
    )
    session.add(audit)

class PolicyValidationErrorException(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__("Policy validation failed")

class PolicyConcurrencyException(Exception):
    pass


async def create_policy(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    data: PolicyCreate,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> Policy:
    tenant_id = principal.tenant_id
    policy = Policy(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
    )

    session.add(policy)
    await session.flush()
    
    record_policy_audit(
        session, principal, "POLICY_CREATED", policy.id,
        after_state=_snapshot_policy(policy),
        request_id=request_id, correlation_id=correlation_id
    )

    version = PolicyVersion(
        tenant_id=tenant_id,
        policy_id=policy.id,
        version=1,
        effect=data.effect,
        priority=data.priority,
        action=data.action,
        resource=data.resource,
        status="active",
    )
    
    validation = validate_policy_version(version, policy)
    if not validation.valid:
        raise PolicyValidationErrorException(validation)

    session.add(version)
    await session.flush()

    policy.active_version_id = version.id
    await session.flush()
    
    policy.active_version = version
    
    record_policy_audit(
        session, principal, "POLICY_VERSION_CREATED", policy.id, version.id,
        after_state=_snapshot_version(version),
        request_id=request_id, correlation_id=correlation_id
    )
    
    return policy

async def activate_policy_version(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    policy_id: str,
    version_id: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> Policy:
    tenant_id = principal.tenant_id
    # Fetch policy and version to activate
    policy_result = await session.execute(
        select(Policy)
        .options(selectinload(Policy.active_version))
        .where(Policy.id == policy_id)
        .with_for_update()
    )
    policy = policy_result.scalars().first()
    if not policy or policy.tenant_id != tenant_id:
        raise ValueError("Policy not found")
        
    version = await session.get(PolicyVersion, version_id)
    if not version or version.tenant_id != tenant_id or version.policy_id != policy_id:
        raise ValueError("Version not found")
        

    # Capture before states
    before_policy = _snapshot_policy(policy)
    before_version = _snapshot_version(version)
    
    # Transition old active
    if policy.active_version:
        policy.active_version.status = "deprecated"
        await session.flush()
    
    version.status = "active"
    policy.active_version_id = version.id
    policy.active_version = version
    
    validation = validate_policy_version(version, policy)

    if not validation.valid:
        raise PolicyValidationErrorException(validation)
        
    try:
        await session.flush()
    except IntegrityError as exc:
        raise PolicyConcurrencyException("Concurrent policy modification detected") from exc
    
    record_policy_audit(
        session, principal, "POLICY_VERSION_ACTIVATED", policy_id, version_id,
        before_state={"policy": before_policy, "target_version": before_version},
        after_state={"policy": _snapshot_policy(policy), "target_version": _snapshot_version(version)},
        request_id=request_id, correlation_id=correlation_id
    )
    return policy



async def list_policies(
    session: AsyncSession,
    tenant_id: str,
) -> list[Policy]:
    result = await session.execute(
        select(Policy)
        .options(selectinload(Policy.active_version))
        .where(Policy.tenant_id == tenant_id)
        .order_by(Policy.created_at.desc())
    )

    return list(result.scalars().all())

async def rollback_policy(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    policy_id: str,
    target_version_id: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> PolicyRollbackResult:
    tenant_id = principal.tenant_id
    policy_result = await session.execute(
        select(Policy)
        .options(selectinload(Policy.active_version))
        .where(Policy.id == policy_id, Policy.tenant_id == tenant_id)
        .with_for_update()
    )
    policy = policy_result.scalars().first()
    if not policy:
        raise ValueError("Policy not found")

    target_result = await session.execute(
        select(PolicyVersion).where(
            PolicyVersion.id == target_version_id,
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.tenant_id == tenant_id,
        )
    )
    target_version = target_result.scalars().first()
    if not target_version:
        raise ValueError("Target version not found")

    before_policy = _snapshot_policy(policy)
    before_target_version = _snapshot_version(target_version)
    before_current_active = None
    current_active = None

    if policy.active_version_id is not None:
        current_active = policy.active_version
        before_current_active = _snapshot_version(current_active)

        if not current_active:
            raise ValueError("Corrupt active version reference")
        if current_active.tenant_id != tenant_id or current_active.policy_id != policy_id:
            raise ValueError("Corrupt active version ownership")
        if current_active.status != "active":
            raise ValueError("Corrupt active version state")
            
        if current_active.id == target_version.id:
            return PolicyRollbackResult(
                policy_id=policy.id,
                previous_active_version_id=target_version.id,
                new_active_version_id=target_version.id,
                changed=False,
                reason="already_active",
            )
            
    detached_target = PolicyVersion(
        id=target_version.id,
        policy_id=target_version.policy_id,
        tenant_id=target_version.tenant_id,
        version=target_version.version,
        effect=target_version.effect,
        priority=target_version.priority,
        action=target_version.action,
        resource=target_version.resource,
        status="active"
    )
    
    validation = validate_policy_version(detached_target, policy)
    if not validation.valid:
        raise PolicyValidationErrorException(validation)

    previous_active_id = None
    if policy.active_version:
        previous_active_id = policy.active_version.id
        policy.active_version.status = "deprecated"
        await session.flush()
        

    target_version.status = "active"
    policy.active_version_id = target_version.id
    policy.active_version = target_version
    
    try:
        await session.flush()
    except IntegrityError as exc:
        raise PolicyConcurrencyException("Concurrent policy modification detected") from exc
    
    record_policy_audit(
        session, principal, "POLICY_VERSION_ROLLED_BACK", policy.id, target_version.id,
        before_state={
            "policy": before_policy,
            "target_version": before_target_version,
            "previous_active_version": before_current_active,
        },
        after_state={
            "policy": _snapshot_policy(policy),
            "target_version": _snapshot_version(target_version),
            "previous_active_version": _snapshot_version(current_active) if current_active else None,
        },
        request_id=request_id, correlation_id=correlation_id
    )
    
    return PolicyRollbackResult(
        policy_id=policy.id,
        previous_active_version_id=previous_active_id,
        new_active_version_id=target_version.id,
        changed=True,
        reason="rollback_applied",
    )
