import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.authorization import ActionRequest
from sentinel_core.execution import ActionExecutor, ExecutionResult, ExecutionStatus
from sentinel_core.action_gateway import enforce_and_execute
from sentinel_core.request_signing import generate_signing_keypair, sign_request, RequestReplayError
from sentinel_core.models import (
    Tenant, Agent, AgentSigningKey, Tool, Capability,
    ToolActionCapability, AgentCapability, Policy, PolicyVersion, ExecutionRecord
)

class MockActionExecutor(ActionExecutor):
    def __init__(self, succeed=True):
        self.call_count = 0
        self.succeed = succeed

    async def execute(self, request, principal):
        self.call_count += 1
        if self.succeed:
            return ExecutionResult(status=ExecutionStatus.EXECUTED, metadata={"status": "ok"})
        return ExecutionResult(status=ExecutionStatus.EXECUTION_FAILED, metadata={"error": "execution error"})

@pytest.mark.asyncio
async def test_idempotency_lifecycle_and_mutation_rejection(session_factory):
    tenant_id = str(uuid4())
    agent_id = str(uuid4())
    tool_id = str(uuid4())
    cap_id = str(uuid4())
    key_id = str(uuid4())
    priv_pem, pub_pem = generate_signing_keypair()

    async with session_factory() as session:
        async with session.begin():
            # Seed tenant
            t = Tenant(id=tenant_id, name=f"T-{tenant_id[:8]}", slug=f"t-{tenant_id[:8]}", status="active")
            session.add(t)
            await session.flush()
            # Seed agent
            ag = Agent(id=agent_id, tenant_id=tenant_id, name="Test Agent", status="active")
            session.add(ag)
            await session.flush()
            # Seed signing key
            sk = AgentSigningKey(id=key_id, agent_id=agent_id, public_key=pub_pem, status="active")
            session.add(sk)
            # Seed tool & capability
            tl = Tool(id=tool_id, tenant_id=tenant_id, name="data_tool", status="active")
            session.add(tl)
            cp = Capability(id=cap_id, tenant_id=tenant_id, name="read_data", description="read")
            session.add(cp)
            await session.flush()
            tac = ToolActionCapability(id=str(uuid4()), tool_id=tool_id, action="read", capability_id=cap_id)
            session.add(tac)
            ac = AgentCapability(id=str(uuid4()), agent_id=agent_id, capability_id=cap_id, resource_scope="*", status="active")
            session.add(ac)
            # Seed policy allowing read
            pol = Policy(id=str(uuid4()), tenant_id=tenant_id, name="allow_read")
            session.add(pol)
            await session.flush()
            pv_id = str(uuid4())
            pv = PolicyVersion(
                id=pv_id,
                policy_id=pol.id,
                tenant_id=tenant_id,
                version=1,
                effect="allow",
                status="active",
                priority=100,
                action="read",
                resource="*",
            )
            session.add(pv)
            await session.flush()
            pol.active_version_id = pv_id
            session.add(pol)

    principal = AuthenticatedPrincipal(agent_id=agent_id, tenant_id=tenant_id, credential_id="c1")
    now = datetime.now(timezone.utc)
    req_id = uuid4()

    req = ActionRequest(
        request_id=req_id,
        agent_id=agent_id,
        tool_id=tool_id,
        action="read",
        resource="res-1",
        context={"query": "initial_query"},
    )
    sig = sign_request(priv_pem, req, principal, now)
    executor = MockActionExecutor(succeed=True)

    # 1. First execution succeeds
    res1 = await enforce_and_execute(
        session_factory=session_factory,
        request=req,
        principal=principal,
        executor=executor,
        signature=sig,
        signing_key_id=key_id,
        timestamp=now,
    )
    assert res1.status == ExecutionStatus.EXECUTED
    assert executor.call_count == 1

    # 2. Exact duplicate retry is idempotent (executor NOT called again)
    res2 = await enforce_and_execute(
        session_factory=session_factory,
        request=req,
        principal=principal,
        executor=executor,
        signature=sig,
        signing_key_id=key_id,
        timestamp=now,
    )
    assert res2.status == ExecutionStatus.EXECUTED
    assert res2.execution_id == res1.execution_id
    assert executor.call_count == 1  # No re-dispatch

    # 3. Mutated payload with same request_id is REJECTED
    mutated_req = ActionRequest(
        request_id=req_id,
        agent_id=agent_id,
        tool_id=tool_id,
        action="read",
        resource="res-1",
        context={"query": "malicious_mutated_query"},
    )
    sig_mutated = sign_request(priv_pem, mutated_req, principal, now)
    with pytest.raises(RequestReplayError):
        await enforce_and_execute(
            session_factory=session_factory,
            request=mutated_req,
            principal=principal,
            executor=executor,
            signature=sig_mutated,
            signing_key_id=key_id,
            timestamp=now,
        )

    # 4. Mutated action with same request_id is REJECTED
    mutated_action_req = ActionRequest(
        request_id=req_id,
        agent_id=agent_id,
        tool_id=tool_id,
        action="delete",
        resource="res-1",
        context={"query": "initial_query"},
    )
    sig_action = sign_request(priv_pem, mutated_action_req, principal, now)
    with pytest.raises(RequestReplayError):
        await enforce_and_execute(
            session_factory=session_factory,
            request=mutated_action_req,
            principal=principal,
            executor=executor,
            signature=sig_action,
            signing_key_id=key_id,
            timestamp=now,
        )
