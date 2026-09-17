import logging
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from sentinel_core.models import SecurityEvent, Incident, DailyAgentSecurityMetric, DailyTenantSecurityMetric

logger = logging.getLogger(__name__)

async def compute_agent_metrics(session: AsyncSession, tenant_id: str, target_date: date) -> None:
    """
    Computes daily agent metrics for a tenant by aggregating SecurityEvents and Incidents.
    """
    
    # 1. Aggregate SecurityEvents
    # SQLite/PostgreSQL Date coercion for the filtering is tricky with datetime columns.
    # For SQLite, we can use func.date() assuming occurred_at is stored correctly, or filter by boundaries.
    
    start_time = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    
    stmt = select(
        SecurityEvent.agent_id,
        func.count().label("total"),
        func.sum(
            case(
                (SecurityEvent.event_type == "POLICY_DENIED", 1),
                else_=0
            )
        ).label("policy_denials"),
        func.sum(
            case(
                (SecurityEvent.event_type == "CAPABILITY_DENIED", 1),
                else_=0
            )
        ).label("capability_denials"),
        func.sum(
            case(
                (SecurityEvent.event_type == "RISK_CRITICAL", 1),
                else_=0
            )
        ).label("critical_risks")
    ).where(
        SecurityEvent.tenant_id == tenant_id,
        SecurityEvent.agent_id.is_not(None),
        SecurityEvent.occurred_at >= start_time,
        SecurityEvent.occurred_at <= end_time
    ).group_by(SecurityEvent.agent_id)
    
    event_result = await session.execute(stmt)
    agent_stats = {row.agent_id: row for row in event_result.all()}
    
    # 2. Aggregate Incidents triggered
    stmt_inc = select(
        Incident.agent_id,
        func.count().label("total")
    ).where(
        Incident.tenant_id == tenant_id,
        Incident.agent_id.is_not(None),
        Incident.created_at >= start_time,
        Incident.created_at <= end_time
    ).group_by(Incident.agent_id)
    
    inc_result = await session.execute(stmt_inc)
    inc_stats = {row.agent_id: row.total for row in inc_result.all()}
    
    all_agents = set(agent_stats.keys()).union(set(inc_stats.keys()))
    
    # Upsert logic (simplistic SQLite specific for this project, generic ORM update otherwise)
    for agent_id in all_agents:
        stats = agent_stats.get(agent_id)
        inc_count = inc_stats.get(agent_id, 0)
        
        policy_d = stats.policy_denials or 0 if stats else 0
        cap_d = stats.capability_denials or 0 if stats else 0
        crit_r = stats.critical_risks or 0 if stats else 0
        total_ev = stats.total or 0 if stats else 0
        
        # Check if exists
        exist_stmt = select(DailyAgentSecurityMetric).where(
            DailyAgentSecurityMetric.tenant_id == tenant_id,
            DailyAgentSecurityMetric.agent_id == agent_id,
            DailyAgentSecurityMetric.metric_date == target_date
        )
        exist_res = await session.execute(exist_stmt)
        record = exist_res.scalars().first()
        
        if record:
            record.total_events = total_ev
            record.policy_denials = policy_d
            record.capability_denials = cap_d
            record.critical_risks = crit_r
            record.incidents_triggered = inc_count
            record.updated_at = datetime.now(timezone.utc)
        else:
            record = DailyAgentSecurityMetric(
                tenant_id=tenant_id,
                agent_id=agent_id,
                metric_date=target_date,
                total_events=total_ev,
                policy_denials=policy_d,
                capability_denials=cap_d,
                critical_risks=crit_r,
                incidents_triggered=inc_count
            )
            session.add(record)
            
    await session.flush()


async def compute_tenant_metrics(session: AsyncSession, tenant_id: str, target_date: date) -> None:
    start_time = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    
    # 1. Total incidents today
    stmt = select(func.count()).where(
        Incident.tenant_id == tenant_id,
        Incident.created_at >= start_time,
        Incident.created_at <= end_time
    )
    inc_count = (await session.execute(stmt)).scalar() or 0
    
    # 2. Unique agents flagged
    stmt_ag = select(func.count(func.distinct(Incident.agent_id))).where(
        Incident.tenant_id == tenant_id,
        Incident.created_at >= start_time,
        Incident.created_at <= end_time,
        Incident.agent_id.is_not(None)
    )
    ag_count = (await session.execute(stmt_ag)).scalar() or 0
    
    exist_stmt = select(DailyTenantSecurityMetric).where(
        DailyTenantSecurityMetric.tenant_id == tenant_id,
        DailyTenantSecurityMetric.metric_date == target_date
    )
    record = (await session.execute(exist_stmt)).scalars().first()
    
    if record:
        record.total_incidents = inc_count
        record.unique_agents_flagged = ag_count
        record.updated_at = datetime.now(timezone.utc)
    else:
        record = DailyTenantSecurityMetric(
            tenant_id=tenant_id,
            metric_date=target_date,
            total_incidents=inc_count,
            unique_agents_flagged=ag_count
        )
        session.add(record)
        
    await session.flush()
