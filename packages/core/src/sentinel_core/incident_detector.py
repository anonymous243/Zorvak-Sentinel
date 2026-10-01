"""
incident_detector.py — F-14: Race-hardened incident detection.

Incident uniqueness is enforced at the DATABASE LEVEL via a partial unique
index on `incidents.dedup_key WHERE status = 'OPEN'`.

Concurrency guarantee:
    Two concurrent workers processing the same logical security condition
    cannot create duplicate OPEN incidents.  The database rejects the second
    INSERT with an IntegrityError; the loser recovers the winner's incident
    via a savepoint rollback + re-query.  The triggering SecurityEvent is
    never lost.

Deduplication key derivation:
    SHA-256("v1:INCIDENT_DEDUP:<tenant_id>:<rule_id>:<agent_id|''>")

    - Deterministic across workers, processes, and retries.
    - Domain-separated ("v1:INCIDENT_DEDUP:") to prevent cross-domain collisions.
    - Excludes volatile timestamps, secrets, and database-generated IDs.
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from sentinel_core.models import Incident, IncidentAuditRecord, SecurityEvent

logger = logging.getLogger(__name__)


class IncidentDetectionConfig:
    # 5 denials within 5 minutes triggers an incident
    THRESHOLD_COUNT = 5
    TIME_WINDOW_MINUTES = 5


# ---------------------------------------------------------------------------
# Public: deduplication key API
# ---------------------------------------------------------------------------

def derive_incident_dedup_key(tenant_id: str, rule_id: str, agent_id: Optional[str]) -> str:
    """
    Derives a deterministic, collision-resistant SHA-256 deduplication key
    for a logical incident identity.

    Key space: one OPEN incident per (tenant, detection_rule, agent).

    Canonical form:
        "v1:INCIDENT_DEDUP:<tenant_id>:<rule_id>:<agent_id_or_empty>"

    Domain prefix ("v1:INCIDENT_DEDUP:") prevents cross-domain hash collisions.
    agent_id=None is normalised to empty string so the key is always defined.
    """
    canonical = f"v1:INCIDENT_DEDUP:{tenant_id}:{rule_id}:{agent_id or ''}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public: detect_incidents_from_event
# ---------------------------------------------------------------------------

async def detect_incidents_from_event(
    session: AsyncSession,
    tenant_id: str,
    event_type: str,
    agent_id: Optional[str],
    occurred_at: datetime,
    session_factory=None,
) -> Optional[Incident]:
    """
    Evaluates detection rules inline for a given incoming SecurityEvent.
    If a threshold is crossed, creates or retrieves a deduplicated Incident.

    This function is called INSIDE the durable SecurityEvent transaction
    (SecurityEventPersistenceService.persist_durable).  It uses SQLAlchemy
    savepoints (begin_nested) so that an IntegrityError during incident
    creation can be rolled back without aborting the outer security-event
    transaction.

    Args:
        session_factory: Optional async_sessionmaker. When provided, the
            IntegrityError recovery path uses it to open a fresh independent
            session that can see the winning worker's committed incident.
            If None, the recovery falls back to session.bind.

    Returns:
        The newly created or pre-existing Incident, or None if no rule fired.
    """

    # 1. Critical Risk Rule (fires on every RISK_CRITICAL event)
    if event_type == "RISK_CRITICAL":
        return await _atomic_create_or_get_incident(
            session,
            tenant_id,
            agent_id,
            rule_id="RULE_CRITICAL_RISK",
            title="Critical Risk Evaluated",
            description="A critical risk evaluation occurred.",
            severity="CRITICAL",
            session_factory=session_factory,
        )

    # 2. Repeated Policy Denials (threshold-based)
    if event_type == "POLICY_DENIED" and agent_id:
        return await _check_threshold_rule(
            session,
            tenant_id,
            agent_id,
            event_type="POLICY_DENIED",
            rule_id="RULE_REPEATED_POLICY_DENIALS",
            title="Repeated Policy Denials",
            description=(
                f"Agent experienced more than {IncidentDetectionConfig.THRESHOLD_COUNT} "
                f"policy denials within {IncidentDetectionConfig.TIME_WINDOW_MINUTES} minutes."
            ),
            severity="HIGH",
            session_factory=session_factory,
        )

    # 3. Repeated Capability Denials (threshold-based)
    if event_type == "CAPABILITY_DENIED" and agent_id:
        return await _check_threshold_rule(
            session,
            tenant_id,
            agent_id,
            event_type="CAPABILITY_DENIED",
            rule_id="RULE_REPEATED_CAPABILITY_DENIALS",
            title="Repeated Capability Denials",
            description=(
                f"Agent experienced more than {IncidentDetectionConfig.THRESHOLD_COUNT} "
                f"capability denials within {IncidentDetectionConfig.TIME_WINDOW_MINUTES} minutes."
            ),
            severity="HIGH",
            session_factory=session_factory,
        )

    return None


# ---------------------------------------------------------------------------
# Private: threshold rule evaluation
# ---------------------------------------------------------------------------

async def _check_threshold_rule(
    session: AsyncSession,
    tenant_id: str,
    agent_id: str,
    event_type: str,
    rule_id: str,
    title: str,
    description: str,
    severity: str,
    session_factory=None,
) -> Optional[Incident]:
    cutoff_time = datetime.now(timezone.utc) - timedelta(
        minutes=IncidentDetectionConfig.TIME_WINDOW_MINUTES
    )

    count_stmt = select(func.count()).where(
        SecurityEvent.tenant_id == tenant_id,
        SecurityEvent.agent_id == agent_id,
        SecurityEvent.event_type == event_type,
        SecurityEvent.occurred_at >= cutoff_time,
    )
    result = await session.execute(count_stmt)
    count = result.scalar() or 0

    if count >= IncidentDetectionConfig.THRESHOLD_COUNT:
        return await _atomic_create_or_get_incident(
            session, tenant_id, agent_id, rule_id, title, description, severity,
            session_factory=session_factory,
        )

    return None


# ---------------------------------------------------------------------------
# Private: atomic create-or-get with savepoint-based race recovery
# ---------------------------------------------------------------------------

async def _atomic_create_or_get_incident(
    session: AsyncSession,
    tenant_id: str,
    agent_id: Optional[str],
    rule_id: str,
    title: str,
    description: str,
    severity: str,
    session_factory=None,
) -> Optional[Incident]:
    """
    Atomically creates a new OPEN incident or retrieves the pre-existing one.

    Race-condition handling:
        1. Derive the deterministic dedup_key.
        2. Open a nested transaction (savepoint).
        3. Attempt INSERT inside the savepoint.
        4a. If INSERT succeeds → commit savepoint → return new incident.
        4b. If INSERT raises IntegrityError (duplicate dedup_key for OPEN) →
               roll back savepoint only (outer SecurityEvent tx is unaffected)
               → re-query the winner's incident → return existing incident.

    The outer security-event transaction is NEVER aborted by an incident race.
    """
    from uuid import uuid4

    dedup_key = derive_incident_dedup_key(tenant_id, rule_id, agent_id)
    now = datetime.now(timezone.utc)
    incident_id = str(uuid4())

    try:
        # Use a SAVEPOINT so that an IntegrityError rolls back only the
        # incident INSERT without poisoning the enclosing transaction.
        async with session.begin_nested():
            incident = Incident(
                id=incident_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                status="OPEN",
                severity=severity,
                detection_rule_id=rule_id,
                title=title,
                description=description,
                dedup_key=dedup_key,
                created_at=now,
                updated_at=now,
            )
            session.add(incident)

            audit = IncidentAuditRecord(
                id=str(uuid4()),
                incident_id=incident_id,
                tenant_id=tenant_id,
                operation="CREATED",
                occurred_at=now,
                actor_id="system",
            )
            session.add(audit)

            # Outbox event for downstream notification
            from sentinel_core import outbox_service
            from sentinel_core.events import IncidentCreatedEvent, serialize_event

            evt = IncidentCreatedEvent(
                incident_id=incident_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                severity=severity,
                detection_rule_id=rule_id,
                title=title,
                occurred_at=now,
            )
            await outbox_service.create_event(
                session=session,
                event_type=evt.event_type,
                aggregate_type="incident",
                aggregate_id=incident_id,
                payload=serialize_event(evt),
                occurred_at=now,
            )

            # flush inside savepoint — triggers the unique constraint check
            await session.flush()

        # Savepoint committed — we created the incident.
        logger.info(
            "Incident created: id=%s tenant=%s rule=%s agent=%s dedup_key=%s",
            incident_id, tenant_id, rule_id, agent_id, dedup_key,
        )

        from sentinel_core import alert_service
        await alert_service.create_alert_from_incident(session, incident)

        return incident

    except IntegrityError:
        # The database rejected our INSERT because a concurrent or previous
        # worker already committed an OPEN incident for the same logical identity.
        # The savepoint was automatically rolled back; the outer transaction
        # (and its SecurityEvent) remain intact.
        logger.info(
            "Incident race resolved: concurrent duplicate suppressed; "
            "retrieving winner for dedup_key=%s tenant=%s rule=%s",
            dedup_key, tenant_id, rule_id,
        )

        # Strategy 1: Re-fetch from the CURRENT session.
        # After a savepoint rollback, the current session can see data committed
        # by other transactions (SQLite: same connection, same tx context).
        # This is the correct approach for SQLite and most scenarios where the
        # winning insert already committed before our savepoint attempt.
        try:
            existing = await _fetch_open_incident(session, tenant_id, rule_id, agent_id)
            if existing:
                logger.info(
                    "Race recovery: found winner %s via current session", existing.id
                )
                return existing
        except Exception as same_session_exc:
            logger.warning(
                "Re-fetch via current session failed: %s", same_session_exc
            )

        # Strategy 2: Fresh independent session.
        # For PostgreSQL with SERIALIZABLE isolation or multi-process concurrency,
        # the current session's MVCC read snapshot may predate the winner's commit.
        # Open a fresh session to see the winner's committed row.
        # NOTE: This will fail on SQLite StaticPool (same connection) but Strategy 1
        # already handles SQLite correctly.
        effective_factory = session_factory
        if effective_factory is None:
            try:
                from sqlalchemy.ext.asyncio import async_sessionmaker as _asm
                engine = session.bind
                if engine is not None:
                    effective_factory = _asm(engine, class_=AsyncSession, expire_on_commit=False)
            except Exception as bind_exc:
                logger.debug("Could not derive factory from session.bind: %s", bind_exc)

        if effective_factory is not None:
            try:
                async with effective_factory() as fresh_session:
                    existing = await _fetch_open_incident(fresh_session, tenant_id, rule_id, agent_id)
                    if existing:
                        logger.info(
                            "Race recovery: found winner %s via fresh session", existing.id
                        )
                        return existing
            except Exception as fresh_exc:
                logger.debug("Re-fetch via fresh session also failed: %s", fresh_exc)

        # Edge case: Both strategies failed.
        # This can happen if the winner's incident was already resolved/closed
        # between the two re-fetch operations.
        # The SecurityEvent is still durable; no duplicate was created.
        logger.warning(
            "IntegrityError during incident creation but no open incident found; "
            "dedup_key=%s tenant=%s rule=%s — treating as no incident.",
            dedup_key, tenant_id, rule_id,
        )
        return None




async def _fetch_open_incident(
    session: AsyncSession,
    tenant_id: str,
    rule_id: str,
    agent_id: Optional[str],
) -> Optional[Incident]:
    """
    Retrieves the authoritative OPEN incident for the given logical identity.
    Used after an IntegrityError race recovery to return the winner's incident.
    """
    stmt = select(Incident).where(
        Incident.tenant_id == tenant_id,
        Incident.detection_rule_id == rule_id,
        Incident.status == "OPEN",
    )
    if agent_id:
        stmt = stmt.where(Incident.agent_id == agent_id)
    else:
        stmt = stmt.where(Incident.agent_id.is_(None))

    result = await session.execute(stmt)
    return result.scalars().first()
