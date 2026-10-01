from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sentinel_core.authorization import ActionRequest
from sentinel_core.models import AgentSigningKey
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.request_signing import verify_request_signature_detailed
from sentinel_core.security_event_service import (
    SecurityEventCreate,
    persist_security_event,
)


SENTINEL_REQUEST_SIGNATURE_MAX_SKEW_SECONDS = 300


async def verify_agent_request_signature(
    session: AsyncSession,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    timestamp: datetime,
    signature: str,
    signing_key_id: str,
    *,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    emit_telemetry: bool = True,
) -> bool:
    """
    Verify a request against an active, non-expired signing key belonging
    to the authenticated agent.

    Verification is fail-closed. A missing, revoked, expired, malformed,
    or otherwise invalid key/signature never authenticates the request.
    On failure, a durable SecurityEvent is persisted.
    """
    now = datetime.now(timezone.utc)

    async def _emit_failure(reason: str) -> None:
        if not emit_telemetry:
            return
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,  # INVARIANT C: Never attribute failed signature to authenticated agent
                credential_id=principal.credential_id,
                tool_id=request.tool_id,
                request_id=str(request.request_id),
                reason_code=reason,
                metadata={
                    "auth_mechanism": "ed25519_signature",
                    "signing_key_id": str(signing_key_id),
                    "failure_category": reason,
                },
            ),
            session_factory=session_factory,
            durable=True,
        )

    # 1. Missing signature
    if not signature or not signature.strip():
        await _emit_failure("missing_signature")
        return False

    # 2. Timestamp validity & skew
    if timestamp is None or getattr(timestamp, "tzinfo", None) is None:
        await _emit_failure("invalid_timestamp")
        return False

    timestamp_utc = timestamp.astimezone(timezone.utc)
    raw_skew = (now - timestamp_utc).total_seconds()

    if raw_skew > SENTINEL_REQUEST_SIGNATURE_MAX_SKEW_SECONDS:
        await _emit_failure("expired_timestamp")
        return False

    if raw_skew < -SENTINEL_REQUEST_SIGNATURE_MAX_SKEW_SECONDS:
        await _emit_failure("future_timestamp")
        return False

    # 3. Signing key lookup
    key_stmt = select(AgentSigningKey).where(
        AgentSigningKey.id == signing_key_id,
        AgentSigningKey.agent_id == principal.agent_id,
    )
    result = await session.execute(key_stmt)
    signing_key = result.scalar_one_or_none()

    if signing_key is None:
        await _emit_failure("unknown_signing_key")
        return False

    if signing_key.status != "active":
        await _emit_failure("revoked_signing_key")
        return False

    # 4. Key expiration
    if signing_key.expires_at is not None:
        expires_at = signing_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            await _emit_failure("expired_signing_key")
            return False

    # 5. Cryptographic signature verification
    valid, fail_reason = verify_request_signature_detailed(
        public_key_pem=signing_key.public_key,
        signature=signature,
        request=request,
        principal=principal,
        timestamp=timestamp,
    )

    if not valid:
        await _emit_failure(fail_reason or "invalid_signature")
        return False

    signing_key.last_used_at = now
    return True

