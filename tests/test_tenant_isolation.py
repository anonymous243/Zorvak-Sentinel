import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sentinel_core.models import (
    Tenant, Agent, AgentSigningKey, Tool, Capability,
    ToolActionCapability, AgentCapability, Policy, PolicyVersion
)
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.authorization import ActionRequest
from sentinel_core.authorization_service import authorize
from sentinel_core.authorization import DecisionEffect

@pytest.mark.asyncio
async def test_tenant_boundary_enforcement(session_factory):
    """
    Verify that an authenticated principal in Tenant A cannot authorize
    or access resources/policies/agents belonging to Tenant B.
    """
    tenant_a_id = str(uuid4())
    tenant_b_id = str(uuid4())
    agent_a_id = str(uuid4())
    agent_b_id = str(uuid4())

    async with session_factory() as session:
        async with session.begin():
            # Seed Tenants
            ta = Tenant(id=tenant_a_id, name=f"TA-{tenant_a_id[:6]}", slug=f"ta-{tenant_a_id[:6]}", status="active")
            tb = Tenant(id=tenant_b_id, name=f"TB-{tenant_b_id[:6]}", slug=f"tb-{tenant_b_id[:6]}", status="active")
            session.add_all([ta, tb])
            await session.flush()

            # Seed Agents
            aga = Agent(id=agent_a_id, tenant_id=tenant_a_id, name="Agent A", status="active")
            agb = Agent(id=agent_b_id, tenant_id=tenant_b_id, name="Agent B", status="active")
            session.add_all([aga, agb])

    principal_a = AuthenticatedPrincipal(agent_id=agent_a_id, tenant_id=tenant_a_id, credential_id="ca")

    # 1. Anti-impersonation: Principal A attempts to execute as Agent B -> rejected immediately
    req_impersonate = ActionRequest(
        request_id=uuid4(),
        agent_id=agent_b_id,  # Trying to impersonate Agent B
        tool_id="some-tool",
        action="read",
        resource="res",
    )
    with pytest.raises(ValueError, match="Anti-impersonation failure"):
        async with session_factory() as session:
            await authorize(session, req_impersonate, principal_a, session_factory=session_factory)

    # 2. Cross-tenant capability/tool access: Agent A attempts to execute action on Tool belonging to Tenant B
    async with session_factory() as session:
        async with session.begin():
            tool_b = Tool(id=str(uuid4()), tenant_id=tenant_b_id, name="b_internal_tool", status="active")
            session.add(tool_b)
            await session.flush()
            cap_b = Capability(id=str(uuid4()), tenant_id=tenant_b_id, name="b_cap", description="secret")
            session.add(cap_b)
            await session.flush()
            tac_b = ToolActionCapability(id=str(uuid4()), tool_id=tool_b.id, action="execute_secret", capability_id=cap_b.id)
            session.add(tac_b)

    req_cross_tool = ActionRequest(
        request_id=uuid4(),
        agent_id=agent_a_id,
        tool_id=tool_b.id,
        action="execute_secret",
        resource="confidential_b_resource",
    )

    async with session_factory() as session:
        decision = await authorize(session, req_cross_tool, principal_a, session_factory=session_factory)
        # Must be strictly DENIED
        assert decision.effect == DecisionEffect.DENY
        assert not decision.allowed
