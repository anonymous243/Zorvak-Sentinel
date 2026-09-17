from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.models import (
    Tool,
    ToolActionCapability,
    Capability,
    AgentCapability
)
from sentinel_core.authorization import DecisionReason

class CapabilityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    allowed: bool
    tool_id: str | None = None
    capability_id: str | None = None
    reason: DecisionReason | None = None
    denial_detail: str | None = None


class ResourceScopeMatcher:
    @staticmethod
    def matches(granted_scope: str, requested_resource: str) -> bool:
        if granted_scope == "*":
            return True
        if granted_scope == requested_resource:
            return True
        return False


async def _check_capability_internal(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    tool_id: str,
    action: str,
    resource: str,
) -> CapabilityResult:
    # 1. Resolve Tool
    tool_res = await session.execute(
        select(Tool)
        .where(Tool.id == tool_id)
        .where(Tool.tenant_id == principal.tenant_id)
    )
    tool = tool_res.scalar_one_or_none()
    if not tool:
        return CapabilityResult(
            allowed=False,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="tool_not_found_or_wrong_tenant"
        )
        
    if tool.status != "active":
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="tool_disabled"
        )
        
    # 2. Resolve ToolActionCapability
    tac_res = await session.execute(
        select(ToolActionCapability)
        .where(ToolActionCapability.tool_id == tool_id)
        .where(ToolActionCapability.action == action)
    )
    tac = tac_res.scalar_one_or_none()
    if not tac:
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="unsupported_action_for_tool"
        )
        
    required_capability_id = tac.capability_id
    
    # 3. Verify Capability Ownership
    cap_res = await session.execute(
        select(Capability)
        .where(Capability.id == required_capability_id)
        .where(Capability.tenant_id == principal.tenant_id)
    )
    cap = cap_res.scalar_one_or_none()
    if not cap:
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            capability_id=required_capability_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="capability_not_found_or_wrong_tenant"
        )
        
    # 4. Verify AgentCapability Grant
    now = datetime.now(timezone.utc)
    ac_res = await session.execute(
        select(AgentCapability)
        .where(AgentCapability.agent_id == principal.agent_id)
        .where(AgentCapability.capability_id == required_capability_id)
    )
    ac = ac_res.scalar_one_or_none()
    
    if not ac:
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            capability_id=required_capability_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="agent_missing_capability"
        )
        
    if ac.status != "active":
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            capability_id=required_capability_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="capability_grant_revoked"
        )
        
    if ac.expires_at and now >= ac.expires_at:
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            capability_id=required_capability_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="capability_grant_expired"
        )
        
    # 5. Verify Resource Scope
    if not ResourceScopeMatcher.matches(ac.resource_scope, resource):
        return CapabilityResult(
            allowed=False,
            tool_id=tool_id,
            capability_id=required_capability_id,
            reason=DecisionReason.CAPABILITY_DENIED,
            denial_detail="resource_scope_mismatch"
        )
        
    # 6. Success
    return CapabilityResult(
        allowed=True,
        tool_id=tool_id,
        capability_id=required_capability_id
    )

async def check_capability(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    tool_id: str,
    action: str,
    resource: str,
) -> CapabilityResult:
    """
    Evaluates if an agent has the required capability to perform an action on a tool.
    Emits a CAPABILITY_DENIED SecurityEvent if evaluation fails.
    """
    result = await _check_capability_internal(session, principal, tool_id, action, resource)
    if not result.allowed:
        from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
        from datetime import datetime, timezone
        
        await persist_security_event(session, SecurityEventCreate(
            tenant_id=principal.tenant_id,
            event_type="CAPABILITY_DENIED",
            occurred_at=datetime.now(timezone.utc),
            outcome="FAILURE",
            agent_id=principal.agent_id,
            credential_id=principal.credential_id,
            tool_id=tool_id,
            reason_code=result.denial_detail or (result.reason.value if hasattr(result.reason, "value") else str(result.reason)),
            metadata={"action": action, "resource": resource, "required_capability_id": result.capability_id}
        ))
    return result
