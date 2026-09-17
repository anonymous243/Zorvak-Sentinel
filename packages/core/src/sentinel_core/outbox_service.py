from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Sequence

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import OutboxEvent

SENTINEL_OUTBOX_MAX_ATTEMPTS = int(os.getenv("SENTINEL_OUTBOX_MAX_ATTEMPTS", "5"))
SENTINEL_OUTBOX_BACKOFF_SECONDS = int(os.getenv("SENTINEL_OUTBOX_BACKOFF_SECONDS", "30"))
SENTINEL_OUTBOX_MAX_BACKOFF_SECONDS = int(os.getenv("SENTINEL_OUTBOX_MAX_BACKOFF_SECONDS", "1800"))
SENTINEL_OUTBOX_LEASE_SECONDS = int(os.getenv("SENTINEL_OUTBOX_LEASE_SECONDS", "300"))
SENTINEL_OUTBOX_BATCH_SIZE = int(os.getenv("SENTINEL_OUTBOX_BATCH_SIZE", "50"))

def _validate_config():
    if SENTINEL_OUTBOX_MAX_ATTEMPTS < 1:
        raise ValueError("max attempts >= 1")
    if SENTINEL_OUTBOX_BACKOFF_SECONDS < 0:
        raise ValueError("backoff >= 0")
    if SENTINEL_OUTBOX_MAX_BACKOFF_SECONDS < 0:
        raise ValueError("max backoff >= 0")
    if SENTINEL_OUTBOX_LEASE_SECONDS <= 0:
        raise ValueError("lease > 0")
    if SENTINEL_OUTBOX_BATCH_SIZE <= 0:
        raise ValueError("batch size > 0")

async def create_event(
    session: AsyncSession,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: str,
    occurred_at: datetime,
    correlation_id: str | None = None,
) -> OutboxEvent:
    _validate_config()
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
        status="pending",
        attempts=0,
        available_at=datetime.now(timezone.utc),
        claimed_at=None,
        lease_until=None,
        claim_token=None,
        published_at=None,
        last_error=None,
    )
    session.add(event)
    return event

async def claim_events(session: AsyncSession, batch_size: int = SENTINEL_OUTBOX_BATCH_SIZE) -> tuple[Sequence[OutboxEvent], str | None]:
    _validate_config()
    now = datetime.now(timezone.utc)
    claim_token = str(uuid.uuid4())
    lease_until = now + timedelta(seconds=SENTINEL_OUTBOX_LEASE_SECONDS)
    
    eligible = or_(
        and_(OutboxEvent.status == "pending", OutboxEvent.available_at <= now),
        and_(
            OutboxEvent.status == "processing",
            OutboxEvent.lease_until.is_not(None),
            OutboxEvent.lease_until <= now,
            OutboxEvent.available_at <= now,
        )
    )

    find_stmt = (
        select(OutboxEvent.id)
        .where(eligible)
        .order_by(OutboxEvent.available_at.asc(), OutboxEvent.created_at.asc(), OutboxEvent.id.asc())
        .limit(batch_size)
    )
    
    result = await session.execute(find_stmt)
    candidate_ids = result.scalars().all()
    
    if not candidate_ids:
        return [], None
        
    update_stmt = (
        update(OutboxEvent)
        .where(
            and_(
                OutboxEvent.id.in_(candidate_ids),
                or_(
                    and_(OutboxEvent.status == "pending", OutboxEvent.available_at <= now),
                    and_(
                        OutboxEvent.status == "processing",
                        OutboxEvent.lease_until.is_not(None),
                        OutboxEvent.lease_until <= now,
                        OutboxEvent.available_at <= now,
                    )
                )
            )
        )
        .values(
            status="processing",
            claimed_at=now,
            lease_until=lease_until,
            claim_token=claim_token,
        )
        .returning(OutboxEvent.id)
    )
    
    update_result = await session.execute(update_stmt)
    claimed_ids = update_result.scalars().all()
    
    if not claimed_ids:
        return [], None
        
    load_stmt = select(OutboxEvent).where(OutboxEvent.claim_token == claim_token).order_by(OutboxEvent.available_at.asc(), OutboxEvent.created_at.asc(), OutboxEvent.id.asc())
    events_res = await session.execute(load_stmt)
    return events_res.scalars().all(), claim_token

async def mark_published(
    session: AsyncSession,
    event_id: str,
    claim_token: str,
) -> bool:
    stmt = (
        update(OutboxEvent)
        .where(
            and_(
                OutboxEvent.id == event_id,
                OutboxEvent.status == "processing",
                OutboxEvent.claim_token == claim_token,
            )
        )
        .values(
            status="published",
            published_at=datetime.now(timezone.utc),
            claimed_at=None,
            lease_until=None,
            claim_token=None,
            last_error=None,
        )
    )
    result = await session.execute(stmt)
    return result.rowcount == 1

async def mark_failed(
    session: AsyncSession,
    event_id: str,
    claim_token: str,
    error_msg: str,
    *,
    max_attempts: int = SENTINEL_OUTBOX_MAX_ATTEMPTS,
    backoff_base: int = SENTINEL_OUTBOX_BACKOFF_SECONDS,
    max_backoff: int = SENTINEL_OUTBOX_MAX_BACKOFF_SECONDS,
) -> bool:
    stmt = select(OutboxEvent.attempts).where(
        and_(
            OutboxEvent.id == event_id,
            OutboxEvent.status == "processing",
            OutboxEvent.claim_token == claim_token,
        )
    )
    res = await session.execute(stmt)
    attempts = res.scalar_one_or_none()
    
    if attempts is None:
        return False
        
    new_attempts = attempts + 1
    now = datetime.now(timezone.utc)
    
    if new_attempts >= max_attempts:
        new_status = "dead_letter"
        next_available = now
    else:
        new_status = "pending"
        delay = min(backoff_base * (2 ** attempts), max_backoff)
        next_available = now + timedelta(seconds=delay)
        
    update_stmt = (
        update(OutboxEvent)
        .where(
            and_(
                OutboxEvent.id == event_id,
                OutboxEvent.status == "processing",
                OutboxEvent.claim_token == claim_token,
                OutboxEvent.attempts == attempts,
            )
        )
        .values(
            status=new_status,
            attempts=new_attempts,
            available_at=next_available,
            last_error=error_msg,
            claimed_at=None,
            lease_until=None,
            claim_token=None,
        )
    )
    upd_res = await session.execute(update_stmt)
    return upd_res.rowcount == 1

async def reclaim_expired_events(
    session: AsyncSession,
    *,
    limit: int = SENTINEL_OUTBOX_BATCH_SIZE,
) -> int:
    _validate_config()
    now = datetime.now(timezone.utc)
    
    find_stmt = select(OutboxEvent.id).where(
        and_(
            OutboxEvent.status == "processing",
            OutboxEvent.lease_until.is_not(None),
            OutboxEvent.lease_until <= now,
        )
    ).limit(limit)
    
    res = await session.execute(find_stmt)
    ids = res.scalars().all()
    
    if not ids:
        return 0
        
    update_stmt = update(OutboxEvent).where(
        and_(
            OutboxEvent.id.in_(ids),
            OutboxEvent.status == "processing",
            OutboxEvent.lease_until.is_not(None),
            OutboxEvent.lease_until <= now,
        )
    ).values(
        status="pending",
        available_at=now,
        claimed_at=None,
        lease_until=None,
        claim_token=None,
    )
    upd_res = await session.execute(update_stmt)
    return upd_res.rowcount

async def get_event(session: AsyncSession, event_id: str) -> OutboxEvent | None:
    res = await session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
    return res.scalar_one_or_none()
