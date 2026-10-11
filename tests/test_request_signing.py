import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.authorization import ActionRequest
from sentinel_core.request_signing import (
    generate_signing_keypair,
    sign_request,
    verify_request_signature,
    compute_request_fingerprint,
    canonicalize_request,
)
from sentinel_core.models import (
    Tenant, Agent, AgentSigningKey, Tool, Capability,
    ToolActionCapability, AgentCapability
)

@pytest.mark.asyncio
async def test_cryptographic_signing_and_verification(session):
    tenant_id = str(uuid4())
    agent_id = str(uuid4())
    priv_pem, pub_pem = generate_signing_keypair()

    principal = AuthenticatedPrincipal(
        agent_id=agent_id,
        tenant_id=tenant_id,
        credential_id="cred-1",
    )
    req = ActionRequest(
        request_id=uuid4(),
        agent_id=agent_id,
        tool_id="sql_tool",
        action="read",
        resource="table_users",
        context={"query": "SELECT 1"},
    )
    now = datetime.now(timezone.utc)
    sig = sign_request(priv_pem, req, principal, now)

    # 1. Valid signature verifies
    assert verify_request_signature(pub_pem, sig, req, principal, now) is True

    # 2. Tampered signature fails
    tampered_sig = "a" * len(sig)
    assert verify_request_signature(pub_pem, tampered_sig, req, principal, now) is False

    # 3. Altered context/payload fails verification (SI-PAYLOAD-BINDING)
    mutated_req = ActionRequest(
        request_id=req.request_id,
        agent_id=agent_id,
        tool_id="sql_tool",
        action="read",
        resource="table_users",
        context={"query": "DROP TABLE users;"},
    )
    assert verify_request_signature(pub_pem, sig, mutated_req, principal, now) is False

    # 4. Fingerprint changes when context/payload changes
    fp_orig = compute_request_fingerprint(req, principal, now)
    fp_mutated = compute_request_fingerprint(mutated_req, principal, now)
    assert fp_orig != fp_mutated

    # 5. Fingerprint is deterministic regardless of dict ordering
    reordered_req = ActionRequest(
        request_id=req.request_id,
        agent_id=agent_id,
        tool_id="sql_tool",
        action="read",
        resource="table_users",
        context={"a": "1", "b": "2"},
    )
    reordered_req2 = ActionRequest(
        request_id=req.request_id,
        agent_id=agent_id,
        tool_id="sql_tool",
        action="read",
        resource="table_users",
        context={"b": "2", "a": "1"},
    )
    assert compute_request_fingerprint(reordered_req, principal, now) == compute_request_fingerprint(reordered_req2, principal, now)
