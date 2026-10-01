import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from sentinel_core.models import (
    SecurityEvent, Incident, Alert, Evidence, 
    Investigation, AuthorizationDecisionRecord, ExecutionRecord
)
from sentinel_core.schemas_analytics import (
    TimeWindow, TrendPoint, EventAnalyticsResponse,
    IncidentAnalyticsResponse, AlertAnalyticsResponse,
    EvidenceAnalyticsResponse, InvestigationAnalyticsResponse,
    ExecutionAnalyticsResponse
)

logger = logging.getLogger(__name__)

def _get_time_bounds(window: TimeWindow) -> Tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    if window == TimeWindow.WINDOW_24H:
        start = end - timedelta(hours=24)
    elif window == TimeWindow.WINDOW_7D:
        start = end - timedelta(days=7)
    elif window == TimeWindow.WINDOW_30D:
        start = end - timedelta(days=30)
    else:
        start = end - timedelta(hours=24)
    return start, end

def _bucket_timestamp(ts: datetime, window: TimeWindow) -> str:
    # Deterministic bucket rounding
    if window == TimeWindow.WINDOW_24H:
        # bucket by hour
        bucket = ts.replace(minute=0, second=0, microsecond=0)
    else:
        # bucket by day
        bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    return bucket.isoformat()

def _build_trend(timestamps: List[datetime], window: TimeWindow) -> List[TrendPoint]:
    counts = defaultdict(int)
    for ts in timestamps:
        # Ensure UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        bucket = _bucket_timestamp(ts, window)
        counts[bucket] += 1
    
    return [TrendPoint(timestamp=k, count=v) for k, v in sorted(counts.items())]


async def get_event_analytics(session: AsyncSession, tenant_id: str, window: TimeWindow) -> EventAnalyticsResponse:
    start_ts, end_ts = _get_time_bounds(window)
    
    stmt = select(SecurityEvent.event_type, SecurityEvent.outcome, SecurityEvent.occurred_at).where(
        and_(
            SecurityEvent.tenant_id == tenant_id,
            SecurityEvent.occurred_at >= start_ts,
            SecurityEvent.occurred_at <= end_ts
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    total = 0
    by_type = defaultdict(int)
    by_outcome = defaultdict(int)
    timestamps = []
    
    for row in rows:
        total += 1
        by_type[row.event_type] += 1
        by_outcome[row.outcome] += 1
        timestamps.append(row.occurred_at)
        
    return EventAnalyticsResponse(
        total_events=total,
        by_type=dict(by_type),
        by_outcome=dict(by_outcome),
        trend=_build_trend(timestamps, window)
    )

async def get_incident_analytics(session: AsyncSession, tenant_id: str, window: TimeWindow) -> IncidentAnalyticsResponse:
    start_ts, end_ts = _get_time_bounds(window)
    stmt = select(Incident.status, Incident.severity, Incident.created_at).where(
        and_(
            Incident.tenant_id == tenant_id,
            Incident.created_at >= start_ts,
            Incident.created_at <= end_ts
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    total = 0
    open_count = 0
    by_sev = defaultdict(int)
    timestamps = []
    
    for row in rows:
        total += 1
        if row.status not in ["CLOSED", "RESOLVED"]:
            open_count += 1
        if row.severity:
            by_sev[row.severity] += 1
        timestamps.append(row.created_at)
        
    return IncidentAnalyticsResponse(
        total_incidents=total,
        open_incidents=open_count,
        by_severity=dict(by_sev),
        trend=_build_trend(timestamps, window)
    )

async def get_alert_analytics(session: AsyncSession, tenant_id: str, window: TimeWindow) -> AlertAnalyticsResponse:
    start_ts, end_ts = _get_time_bounds(window)
    stmt = select(Alert.status, Alert.created_at).where(
        and_(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_ts,
            Alert.created_at <= end_ts
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    total = 0
    by_status = defaultdict(int)
    timestamps = []
    
    for row in rows:
        total += 1
        by_status[row.status] += 1
        timestamps.append(row.created_at)
        
    return AlertAnalyticsResponse(
        total_alerts=total,
        by_status=dict(by_status),
        trend=_build_trend(timestamps, window)
    )

async def get_evidence_analytics(session: AsyncSession, tenant_id: str, window: TimeWindow) -> EvidenceAnalyticsResponse:
    start_ts, end_ts = _get_time_bounds(window)
    stmt = select(Evidence.id).where(
        and_(
            Evidence.tenant_id == tenant_id,
            Evidence.created_at >= start_ts,
            Evidence.created_at <= end_ts
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    return EvidenceAnalyticsResponse(total_evidence=len(rows))

async def get_investigation_analytics(session: AsyncSession, tenant_id: str, window: TimeWindow) -> InvestigationAnalyticsResponse:
    start_ts, end_ts = _get_time_bounds(window)
    stmt = select(Investigation.status, Investigation.created_at).where(
        and_(
            Investigation.tenant_id == tenant_id,
            Investigation.created_at >= start_ts,
            Investigation.created_at <= end_ts
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    total = 0
    by_status = defaultdict(int)
    timestamps = []
    
    for row in rows:
        total += 1
        by_status[row.status] += 1
        timestamps.append(row.created_at)
        
    return InvestigationAnalyticsResponse(
        total_investigations=total,
        by_status=dict(by_status),
        trend=_build_trend(timestamps, window)
    )

async def get_execution_analytics(session: AsyncSession, tenant_id: str, window: TimeWindow) -> ExecutionAnalyticsResponse:
    start_ts, end_ts = _get_time_bounds(window)
    stmt = select(AuthorizationDecisionRecord.effect, AuthorizationDecisionRecord.evaluated_at).where(
        and_(
            AuthorizationDecisionRecord.tenant_id == tenant_id,
            AuthorizationDecisionRecord.evaluated_at >= start_ts,
            AuthorizationDecisionRecord.evaluated_at <= end_ts
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    total = 0
    by_effect = defaultdict(int)
    timestamps = []
    
    for row in rows:
        total += 1
        if isinstance(row.effect, str):
            by_effect[row.effect] += 1
        elif hasattr(row.effect, 'name'):
            by_effect[row.effect.name] += 1
        else:
            by_effect[str(row.effect)] += 1
        timestamps.append(row.evaluated_at)
        
    return ExecutionAnalyticsResponse(
        total_decisions=total,
        by_effect=dict(by_effect),
        trend=_build_trend(timestamps, window)
    )
