import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select
from sentinel_core.delegation_service import (
    create_delegation,
    revoke_delegation,
    validate_delegated_request,
    sign_delegation,
)
from sentinel_core.request_signing import generate_signing_keypair
from sentinel_core.models import (
    Tenant, Agent, AgentSigningKey, AgentTrustRelationship, AgentDelegation,
    Tool, Capability, ToolActionCapability, AgentCapability
)
from sentinel_core.authorization import ActionRequest
from sentinel_core.principals import AuthenticatedPrincipal

@pytest.mark.asyncio
async def test_delegation_transitive_monotonicity_and_escalation(session_factory):
    tenant_id = str(uuid4())
    root_agent_id = str(uuid4())
    intermediate_agent_id = str(uuid4())
    leaf_agent_id = str(uuid4())

    priv_pem, pub_pem = generate_signing_keypair()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=2)

    async with session_factory() as session:
        async with session.begin():
            # Seed tenant
            t = Tenant(id=tenant_id, name=f"T-{tenant_id[:8]}", slug=f"t-{tenant_id[:8]}", status="active")
            session.add(t)
            await session.flush()

            # Seed 3 agents
            a1 = Agent(id=root_agent_id, tenant_id=tenant_id, name="Root Agent", status="active")
            a2 = Agent(id=intermediate_agent_id, tenant_id=tenant_id, name="Inter Agent", status="active")
            a3 = Agent(id=leaf_agent_id, tenant_id=tenant_id, name="Leaf Agent", status="active")
            session.add_all([a1, a2, a3])
            await session.flush()

            # Key for root agent
            k1 = AgentSigningKey(id=str(uuid4()), agent_id=root_agent_id, public_key=pub_pem, status="active")
            session.add(k1)
            # Key for intermediate agent
            k2 = AgentSigningKey(id=str(uuid4()), agent_id=intermediate_agent_id, public_key=pub_pem, status="active")
            session.add(k2)

            # Tool & capability granting root agent 'read' on 'tenant/orders/*'
            cap_id = str(uuid4())
            tool_id = str(uuid4())
            tool = Tool(id=tool_id, tenant_id=tenant_id, name="order_tool", status="active")
            cap = Capability(id=cap_id, tenant_id=tenant_id, name="read_orders", description="read orders")
            session.add_all([tool, cap])
            await session.flush()

            tac = ToolActionCapability(id=str(uuid4()), tool_id=tool_id, action="read", capability_id=cap_id)
            ac = AgentCapability(
                id=str(uuid4()),
                agent_id=root_agent_id,
                capability_id=cap_id,
                resource_scope="tenant/orders/*",
                status="active"
            )
            session.add_all([tac, ac])

            # Trust 1: root -> intermediate
            tr1 = AgentTrustRelationship(
                id=str(uuid4()),
                tenant_id=tenant_id,
                source_agent_id=root_agent_id,
                target_agent_id=intermediate_agent_id,
                status="ACTIVE",
            )
            # Trust 2: intermediate -> leaf
            tr2 = AgentTrustRelationship(
                id=str(uuid4()),
                tenant_id=tenant_id,
                source_agent_id=intermediate_agent_id,
                target_agent_id=leaf_agent_id,
                status="ACTIVE",
            )
            session.add_all([tr1, tr2])

    # 1. Create Parent delegation: root -> intermediate with restricted resource "tenant/orders/*" and action "read"
    parent_del_id = str(uuid4())
    parent_sig = sign_delegation(
        private_key_pem=priv_pem,
        delegation_id=parent_del_id,
        tenant_id=tenant_id,
        delegator_agent_id=root_agent_id,
        delegate_agent_id=intermediate_agent_id,
        trust_relationship_id=tr1.id,
        action_scope=["read"],
        resource_scope=["tenant/orders/*"],
        capability_scope=[cap_id],
        issued_at=now,
        expires_at=expires,
        parent_delegation_id=None,
    )

    async with session_factory() as session:
        async with session.begin():
            await create_delegation(
                session=session,
                tenant_id=tenant_id,
                delegation_id=parent_del_id,
                delegator_agent_id=root_agent_id,
                delegate_agent_id=intermediate_agent_id,
                action_scope=["read"],
                resource_scope=["tenant/orders/*"],
                capability_scope=[cap_id],
                issued_at=now,
                expires_at=expires,
                signing_key_id=k1.id,
                signature=parent_sig,
                parent_delegation_id=None,
                allow_transitive=True,
                session_factory=session_factory,
            )

    # 2. Transitive child delegation attempting resource escalation (requesting "*" when parent only allows "tenant/orders/*")
    child_del_id_escalation = str(uuid4())
    child_sig_escalation = sign_delegation(
        private_key_pem=priv_pem,
        delegation_id=child_del_id_escalation,
        tenant_id=tenant_id,
        delegator_agent_id=intermediate_agent_id,
        delegate_agent_id=leaf_agent_id,
        trust_relationship_id=tr2.id,
        action_scope=["read"],
        resource_scope=["*"],  # ESCALATION!
        capability_scope=[cap_id],
        issued_at=now,
        expires_at=expires,
        parent_delegation_id=parent_del_id,
    )

    with pytest.raises(ValueError, match="Transitive delegation escalation"):
        async with session_factory() as session:
            async with session.begin():
                await create_delegation(
                    session=session,
                    tenant_id=tenant_id,
                    delegation_id=child_del_id_escalation,
                    delegator_agent_id=intermediate_agent_id,
                    delegate_agent_id=leaf_agent_id,
                    action_scope=["read"],
                    resource_scope=["*"],
                    capability_scope=[cap_id],
                    issued_at=now,
                    expires_at=expires,
                    signing_key_id=k2.id,
                    signature=child_sig_escalation,
                    parent_delegation_id=parent_del_id,
                    allow_transitive=True,
                    session_factory=session_factory,
                )

    # 3. Transitive child delegation attempting action escalation (requesting "write" when parent only allows "read")
    child_del_id_action_esc = str(uuid4())
    child_sig_action_esc = sign_delegation(
        private_key_pem=priv_pem,
        delegation_id=child_del_id_action_esc,
        tenant_id=tenant_id,
        delegator_agent_id=intermediate_agent_id,
        delegate_agent_id=leaf_agent_id,
        trust_relationship_id=tr2.id,
        action_scope=["read", "write"],  # ACTION ESCALATION!
        resource_scope=["tenant/orders/*"],
        capability_scope=[cap_id],
        issued_at=now,
        expires_at=expires,
        parent_delegation_id=parent_del_id,
    )

    with pytest.raises(ValueError, match="Transitive delegation escalation"):
        async with session_factory() as session:
            async with session.begin():
                await create_delegation(
                    session=session,
                    tenant_id=tenant_id,
                    delegation_id=child_del_id_action_esc,
                    delegator_agent_id=intermediate_agent_id,
                    delegate_agent_id=leaf_agent_id,
                    action_scope=["read", "write"],
                    resource_scope=["tenant/orders/*"],
                    capability_scope=[cap_id],
                    issued_at=now,
                    expires_at=expires,
                    signing_key_id=k2.id,
                    signature=child_sig_action_esc,
                    parent_delegation_id=parent_del_id,
                    allow_transitive=True,
                    session_factory=session_factory,
                )

    # 4. Transitive child delegation strictly monotonically scoped (allowed subset)
    child_valid_id = str(uuid4())
    child_sig_valid = sign_delegation(
        private_key_pem=priv_pem,
        delegation_id=child_valid_id,
        tenant_id=tenant_id,
        delegator_agent_id=intermediate_agent_id,
        delegate_agent_id=leaf_agent_id,
        trust_relationship_id=tr2.id,
        action_scope=["read"],
        resource_scope=["tenant/orders/123"],  # Specific subset of "tenant/orders/*"
        capability_scope=[cap_id],
        issued_at=now,
        expires_at=expires,
        parent_delegation_id=parent_del_id,
    )

    async with session_factory() as session:
        async with session.begin():
            created_child = await create_delegation(
                session=session,
                tenant_id=tenant_id,
                delegation_id=child_valid_id,
                delegator_agent_id=intermediate_agent_id,
                delegate_agent_id=leaf_agent_id,
                action_scope=["read"],
                resource_scope=["tenant/orders/123"],
                capability_scope=[cap_id],
                issued_at=now,
                expires_at=expires,
                signing_key_id=k2.id,
                signature=child_sig_valid,
                parent_delegation_id=parent_del_id,
                allow_transitive=True,
                session_factory=session_factory,
            )
            assert created_child is not None
            assert created_child.status == "ACTIVE"
