from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Mapping, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sentinel_core.models import SecurityEvent

FORBIDDEN_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "jwt",
    "cookie",
    "private_key",
    "signing_key",
    "authorization",
    "api_key",
    "apikey",
    "credential",
)

SYSTEM_TENANT_ID: str = "00000000-0000-0000-0000-000000000000"



def sanitize_metadata(data: Any, depth: int = 0) -> Any:
    """
    Recursively sanitizes event metadata to ensure secrets, tokens,
    cookies, credentials, and private keys are never stored in telemetry.
    """
    if depth > 5:
        return "<max_depth_exceeded>"
    if isinstance(data, Mapping):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower().strip()
            if any(forbidden in k_lower for forbidden in FORBIDDEN_SUBSTRINGS):
                continue
            sanitized[str(k)] = sanitize_metadata(v, depth + 1)
        return sanitized
    elif isinstance(data, (list, tuple)):
        return [sanitize_metadata(item, depth + 1) for item in data]
    elif isinstance(data, str):
        # Redact raw PEM private keys
        if "BEGIN" in data and "PRIVATE KEY" in data:
            return "[REDACTED_PRIVATE_KEY]"
        # Redact potential JWTs (3 segments separated by dots, starting with eyJ)
        if data.startswith("eyJ") and data.count(".") == 2:
            return "[REDACTED_JWT]"
        return data
    elif isinstance(data, (int, float, bool)) or data is None:
        return data
    else:
        return str(data)


class SecurityEventCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    occurred_at: datetime
    outcome: str = Field(..., min_length=1)

    event_id: Optional[str] = None
    agent_id: Optional[str] = None
    credential_id: Optional[str] = None
    tool_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version_id: Optional[str] = None
    execution_id: Optional[str] = None
    authorization_decision_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None

    reason_code: Optional[str] = None
    metadata: Optional[Mapping[str, Any]] = None


class SecurityEventPersistenceService:
    """
    Enterprise-grade security telemetry persistence service.

    Enforces:
      - Independent transaction durability (survives business rollbacks)
      - Authoritative tenant isolation (prevents cross-tenant event injection)
      - Deterministic event idempotency (avoids duplicate logical telemetry)
      - Strict secret exclusion (sanitizes metadata)
      - Inline incident detection inside the event's durable transaction
    """

    @classmethod
    async def persist_durable(
        cls,
        event: SecurityEventCreate,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
        principal: Optional[Any] = None,
    ) -> SecurityEvent:
        # 1. Validation
        if event.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware (UTC)")

        if principal is not None:
            if hasattr(principal, "tenant_id") and event.tenant_id != principal.tenant_id:
                raise ValueError(
                    f"Cross-tenant event injection rejected: event tenant_id '{event.tenant_id}' "
                    f"does not match principal tenant_id '{principal.tenant_id}'"
                )

        # 2. Resolve independent session factory
        if session_factory is not None:
            factory = session_factory
        elif session is not None and getattr(session, "bind", None) is not None:
            factory = async_sessionmaker(session.bind, class_=AsyncSession, expire_on_commit=False)
        else:
            from sentinel_core.database import SessionFactory
            factory = SessionFactory

        # 3. Sanitize metadata payload
        metadata_json = None
        if event.metadata:
            sanitized = sanitize_metadata(event.metadata)
            metadata_json = json.dumps(sanitized, ensure_ascii=True, separators=(',', ':'))

        event_id = event.event_id or str(uuid4())

        # 4. Independent transaction boundary
        async with factory() as evt_session:
            async with evt_session.begin():
                # Check idempotency first if event_id is explicit
                if event.event_id:
                    existing = await evt_session.get(SecurityEvent, event.event_id)
                    if existing:
                        return existing

                db_event = SecurityEvent(
                    id=event_id,
                    tenant_id=event.tenant_id,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    outcome=event.outcome,
                    agent_id=event.agent_id,
                    credential_id=event.credential_id,
                    tool_id=event.tool_id,
                    policy_id=event.policy_id,
                    policy_version_id=event.policy_version_id,
                    execution_id=event.execution_id,
                    authorization_decision_id=event.authorization_decision_id,
                    correlation_id=event.correlation_id,
                    request_id=event.request_id,
                    reason_code=event.reason_code,
                    metadata_payload=metadata_json,
                    created_at=datetime.now(timezone.utc),
                )

                try:
                    print(f"Adding security event {event_id} to evt_session")
                    evt_session.add(db_event)
                    print(f"Flushing evt_session for {event_id}")
                    await evt_session.flush()
                    print(f"Flushed evt_session for {event_id}")
                except IntegrityError:
                    if event.event_id:
                        # Concurrent race for identical event_id -> fetch and return winner
                        await evt_session.rollback()
                        async with factory() as retry_session:
                            winner = await retry_session.get(SecurityEvent, event.event_id)
                            if winner:
                                return winner
                    raise

                from sentinel_core.incident_detector import detect_incidents_from_event
                print(f"Calling detect_incidents_from_event for {event_id}")
                await detect_incidents_from_event(
                    session=evt_session,
                    tenant_id=db_event.tenant_id,
                    event_type=db_event.event_type,
                    agent_id=db_event.agent_id,
                    occurred_at=db_event.occurred_at,
                    session_factory=factory,
                )
                print(f"Finished detect_incidents_from_event for {event_id}")

        return db_event

    @classmethod
    async def persist_in_session(
        cls,
        session: AsyncSession,
        event: SecurityEventCreate,
        *,
        principal: Optional[Any] = None,
    ) -> SecurityEvent:
        """
        Persists within caller-provided session without independent commit (flush only).
        """
        if event.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware (UTC)")

        if principal is not None:
            if hasattr(principal, "tenant_id") and event.tenant_id != principal.tenant_id:
                raise ValueError(
                    f"Cross-tenant event injection rejected: event tenant_id '{event.tenant_id}' "
                    f"does not match principal tenant_id '{principal.tenant_id}'"
                )

        metadata_json = None
        if event.metadata:
            sanitized = sanitize_metadata(event.metadata)
            metadata_json = json.dumps(sanitized, ensure_ascii=True, separators=(',', ':'))

        event_id = event.event_id or str(uuid4())

        db_event = SecurityEvent(
            id=event_id,
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            outcome=event.outcome,
            agent_id=event.agent_id,
            credential_id=event.credential_id,
            tool_id=event.tool_id,
            policy_id=event.policy_id,
            policy_version_id=event.policy_version_id,
            execution_id=event.execution_id,
            authorization_decision_id=event.authorization_decision_id,
            correlation_id=event.correlation_id,
            request_id=event.request_id,
            reason_code=event.reason_code,
            metadata_payload=metadata_json,
            created_at=datetime.now(timezone.utc),
        )

        session.add(db_event)
        await session.flush()

        from sentinel_core.incident_detector import detect_incidents_from_event
        await detect_incidents_from_event(
            session=session,
            tenant_id=db_event.tenant_id,
            event_type=db_event.event_type,
            agent_id=db_event.agent_id,
            occurred_at=db_event.occurred_at,
        )

        return db_event


async def persist_security_event(
    session: AsyncSession | None,
    event: SecurityEventCreate,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    durable: bool = True,
    principal: Optional[Any] = None,
) -> SecurityEvent:
    """
    Persists a deterministic security event.

    When durable=True (default), the event is committed in an independent database
    transaction so that it remains durable even if the caller's business transaction
    is rolled back.

    When durable=False, the event is flushed into the caller's session without commit.
    """
    if durable:
        return await SecurityEventPersistenceService.persist_durable(
            event=event,
            session_factory=session_factory,
            session=session,
            principal=principal,
        )
    else:
        if session is None:
            raise ValueError("session is required when durable=False")
        return await SecurityEventPersistenceService.persist_in_session(
            session=session,
            event=event,
            principal=principal,
        )


persist_security_event_durable = SecurityEventPersistenceService.persist_durable
