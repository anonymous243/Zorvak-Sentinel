import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sentinel_core.models import Tenant, SecurityEvent
from sentinel_core.security_event_service import (
    persist_security_event,
    SecurityEventCreate,
    sanitize_metadata,
)
from sentinel_core.principals import AuthenticatedPrincipal

@pytest.mark.asyncio
async def test_security_event_durability_across_rollback(session_factory):
    tenant_id = str(uuid4())
    event_id = str(uuid4())
    now = datetime.now(timezone.utc)

    # 1. Seed tenant in a clean transaction
    async with session_factory() as session:
        async with session.begin():
            t = Tenant(id=tenant_id, name=f"T-{tenant_id[:8]}", slug=f"t-{tenant_id[:8]}", status="active")
            session.add(t)

    # 2. Open a business transaction, persist a DURABLE security event, and ROLL BACK the business transaction
    try:
        async with session_factory() as business_session:
            async with business_session.begin():
                # Perform an action that fails or triggers a rollback
                event = SecurityEventCreate(
                    event_id=event_id,
                    tenant_id=tenant_id,
                    event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
                    occurred_at=now,
                    outcome="FAILURE",
                    reason_code="token_invalid",
                    metadata={
                        "attempted_path": "/api/v1/secure",
                        "password": "SHOULD_BE_REDACTED",  # Sensitive field must be stripped
                        "safe_info": "logged_safely",
                    },
                )
                # Durable event write to independent transaction boundary
                await persist_security_event(
                    session=business_session,
                    event=event,
                    session_factory=session_factory,
                    durable=True,
                )
                # Now force an error in the primary business transaction to trigger rollback!
                raise RuntimeError("Simulated business transaction failure")
    except RuntimeError:
        pass  # Expected rollback

    # 3. Verify the security event survived the business transaction rollback in PostgreSQL
    async with session_factory() as verify_session:
        res = await verify_session.execute(
            select(SecurityEvent).where(SecurityEvent.id == event_id)
        )
        saved_event = res.scalar_one_or_none()
        assert saved_event is not None
        assert saved_event.tenant_id == tenant_id
        assert saved_event.event_type == "UNAUTHORIZED_ACCESS_ATTEMPT"
        assert saved_event.outcome == "FAILURE"
        # Verify secret sanitization occurred
        assert "password" not in saved_event.metadata_payload
        assert "SHOULD_BE_REDACTED" not in saved_event.metadata_payload
        assert "safe_info" in saved_event.metadata_payload

@pytest.mark.asyncio
async def test_cross_tenant_security_event_rejection(session_factory):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    principal_a = AuthenticatedPrincipal(agent_id=str(uuid4()), tenant_id=tenant_a, credential_id="c1")

    event_cross = SecurityEventCreate(
        tenant_id=tenant_b,  # Attacking cross-tenant injection!
        event_type="REPLAY_ATTEMPT",
        occurred_at=datetime.now(timezone.utc),
        outcome="FAILURE",
    )

    with pytest.raises(ValueError, match="Cross-tenant event injection rejected"):
        await persist_security_event(
            session=None,
            event=event_cross,
            session_factory=session_factory,
            principal=principal_a,
            durable=True,
        )
