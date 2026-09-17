from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.authorization import ActionRequest
from sentinel_core.models import AgentSigningKey
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.request_signing import verify_request_signature


async def verify_agent_request_signature(
    session: AsyncSession,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
    signature: str,
    signing_key_id: str,
) -> bool:
    """
    Verify a request against an active, non-expired signing key belonging
    to the authenticated agent.

    Verification is fail-closed. A missing, revoked, expired, malformed,
    or otherwise invalid key/signature never authenticates the request.
    """

    if timestamp.tzinfo is None:
        return False

    now = datetime.now(timezone.utc)
    timestamp_utc = timestamp.astimezone(timezone.utc)
    
    SENTINEL_REQUEST_SIGNATURE_MAX_SKEW_SECONDS = 300
    skew = abs((now - timestamp_utc).total_seconds())
    
    if skew > SENTINEL_REQUEST_SIGNATURE_MAX_SKEW_SECONDS:
        return False

    result = await session.execute(
        select(AgentSigningKey)
        .where(AgentSigningKey.id == signing_key_id)
        .where(AgentSigningKey.agent_id == principal.agent_id)
        .where(AgentSigningKey.status == "active")
    )

    signing_key = result.scalar_one_or_none()

    if signing_key is None:
        return False

    if signing_key.expires_at is not None:
        expires_at = signing_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            return False

    valid = verify_request_signature(
        public_key_pem=signing_key.public_key,
        signature=signature,
        request=request,
        principal=principal,
        timestamp=timestamp,
    )

    if not valid:
        return False

    signing_key.last_used_at = now
    return True
