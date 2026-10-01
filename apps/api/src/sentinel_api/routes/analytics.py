from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sentinel_core.database import get_session
from sentinel_core.rbac import require_role
from sentinel_core.schemas_human import CurrentUserContext
from sentinel_core.schemas_analytics import (
    TimeWindow, EventAnalyticsResponse, IncidentAnalyticsResponse,
    AlertAnalyticsResponse, EvidenceAnalyticsResponse,
    InvestigationAnalyticsResponse, ExecutionAnalyticsResponse
)
from sentinel_core import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/events", response_model=EventAnalyticsResponse)
async def get_events(
    window: TimeWindow = Query(default=TimeWindow.WINDOW_24H),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
):
    return await analytics_service.get_event_analytics(session, tenant_id, window)

@router.get("/incidents", response_model=IncidentAnalyticsResponse)
async def get_incidents(
    window: TimeWindow = Query(default=TimeWindow.WINDOW_24H),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
):
    return await analytics_service.get_incident_analytics(session, tenant_id, window)

@router.get("/alerts", response_model=AlertAnalyticsResponse)
async def get_alerts(
    window: TimeWindow = Query(default=TimeWindow.WINDOW_24H),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
):
    return await analytics_service.get_alert_analytics(session, tenant_id, window)

@router.get("/evidence", response_model=EvidenceAnalyticsResponse)
async def get_evidence(
    window: TimeWindow = Query(default=TimeWindow.WINDOW_24H),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
):
    return await analytics_service.get_evidence_analytics(session, tenant_id, window)

@router.get("/investigations", response_model=InvestigationAnalyticsResponse)
async def get_investigations(
    window: TimeWindow = Query(default=TimeWindow.WINDOW_24H),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
):
    return await analytics_service.get_investigation_analytics(session, tenant_id, window)

@router.get("/executions", response_model=ExecutionAnalyticsResponse)
async def get_executions(
    window: TimeWindow = Query(default=TimeWindow.WINDOW_24H),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
):
    return await analytics_service.get_execution_analytics(session, tenant_id, window)
