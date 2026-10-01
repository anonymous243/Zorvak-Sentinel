from datetime import datetime, timezone
from typing import Optional

import bcrypt
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sentinel_core.models import Agent, AgentCredential, Tenant
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.security_event_service import (
    SYSTEM_TENANT_ID,
    SecurityEventCreate,
    persist_security_event,
)


class AuthenticationError(Exception):
    """Raised when authentication fails for any reason."""
    pass


async def authenticate_agent(
    session: AsyncSession,
    agent_id: str,
    secret: SecretStr,
    *,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> AuthenticatedPrincipal:
    """
    Authenticates an agent given their stable agent_id and a secret credential.
    
    This function implements a strict fail-closed boundary. It returns an
    AuthenticatedPrincipal only if:
    - The agent exists and is active.
    - The agent's tenant exists and is active.
    - An active credential exists for the agent.
    - The provided secret matches the bcrypt hash of the active credential.
    - The credential has not expired.
    
    Any failure records a durable SecurityEvent and immediately raises AuthenticationError.
    """
    now = datetime.now(timezone.utc)

    async def _emit_failure(
        *,
        tenant_id: str,
        reason_code: str,
        credential_id: Optional[str] = None,
    ) -> None:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=tenant_id,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,  # INVARIANT C: Never attribute failed attempt as authenticated agent
                credential_id=credential_id,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code=reason_code,
                metadata={
                    "auth_mechanism": "agent_credential",
                    "claimed_agent_id": str(agent_id),
                    "failure_category": reason_code,
                },

            ),
            session_factory=session_factory,
            durable=True,
        )

    # 1. Fetch Agent
    agent_stmt = select(Agent).where(Agent.id == agent_id)
    agent_res = await session.execute(agent_stmt)
    agent = agent_res.scalar_one_or_none()

    if not agent:
        await _emit_failure(
            tenant_id=SYSTEM_TENANT_ID,
            reason_code="unknown_agent",
        )
        raise AuthenticationError("Authentication failed")

    # 2. Fetch Tenant
    tenant_stmt = select(Tenant).where(Tenant.id == agent.tenant_id)
    tenant_res = await session.execute(tenant_stmt)
    tenant = tenant_res.scalar_one_or_none()

    if not tenant or tenant.status != "active":
        await _emit_failure(
            tenant_id=agent.tenant_id,
            reason_code="inactive_tenant",
        )
        raise AuthenticationError("Authentication failed")

    # 3. Check Agent Status
    if agent.status != "active":
        await _emit_failure(
            tenant_id=agent.tenant_id,
            reason_code="inactive_agent",
        )
        raise AuthenticationError("Authentication failed")

    # 4. Fetch Credentials
    all_creds_stmt = select(AgentCredential).where(AgentCredential.agent_id == agent_id)
    all_creds_res = await session.execute(all_creds_stmt)
    all_creds = all_creds_res.scalars().all()

    if not all_creds:
        await _emit_failure(
            tenant_id=agent.tenant_id,
            reason_code="unknown_credential",
        )
        raise AuthenticationError("Authentication failed")

    active_creds = [c for c in all_creds if c.status == "active"]
    if not active_creds:
        await _emit_failure(
            tenant_id=agent.tenant_id,
            reason_code="revoked_credential",
        )
        raise AuthenticationError("Authentication failed")

    def _normalize_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    # 5. Verify Secret against Hashes
    valid_credential = None
    provided_secret = secret.get_secret_value().encode("utf-8")
    expired_match_found = False
    expired_cred_id = None

    for cred in all_creds:
        if bcrypt.checkpw(provided_secret, cred.secret_hash.encode("utf-8")):
            if cred.status != "active":
                continue
            exp = _normalize_utc(cred.expires_at)
            if exp and exp < now:
                expired_match_found = True
                expired_cred_id = cred.id
                continue
            valid_credential = cred
            break

    if not valid_credential:
        if expired_match_found:
            reason = "expired_credential"
            cred_id = expired_cred_id
        else:
            all_active_expired = all(
                (exp := _normalize_utc(c.expires_at)) is not None and exp < now
                for c in active_creds
            )
            if all_active_expired and active_creds:
                reason = "expired_credential"
                cred_id = None
            else:
                reason = "invalid_credential"
                cred_id = None

        await _emit_failure(
            tenant_id=agent.tenant_id,
            reason_code=reason,
            credential_id=cred_id,
        )
        raise AuthenticationError("Authentication failed")


    # 6. Update last_used_at
    valid_credential.last_used_at = now

    await persist_security_event(
        session=session,
        event=SecurityEventCreate(
            tenant_id=agent.tenant_id,
            event_type="AUTHENTICATION_SUCCESS",
            occurred_at=now,
            outcome="SUCCESS",
            agent_id=agent.id,
            credential_id=valid_credential.id,
            request_id=request_id,
            correlation_id=correlation_id,
        ),
        session_factory=session_factory,
        durable=True,
    )

    # 7. Return Principal
    return AuthenticatedPrincipal(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        credential_id=valid_credential.id,
    )

