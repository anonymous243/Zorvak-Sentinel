from typing import Any, Sequence, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.database import get_session
from sentinel_core.rbac import require_role
from sentinel_core.schemas_human import CurrentUserContext
from sentinel_core import alert_service
from sentinel_core.models import Alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_id: str
    status: str
    severity: str
    title: str
    description: str
    created_at: Any
    updated_at: Any
    acknowledged_at: Optional[Any] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[Any] = None
    resolved_by: Optional[str] = None


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, ACKNOWLEDGED, RESOLVED)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
) -> Sequence[Alert]:
    alerts = await alert_service.list_alerts(session, tenant_id, status, limit, offset)
    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
) -> Alert:
    alert = await alert_service.get_alert(session, tenant_id, str(alert_id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
) -> Alert:
    actor = context.user.id
    try:
        alert = await alert_service.acknowledge_alert(session, tenant_id, str(alert_id), actor)
        await session.commit()
        return alert
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Alert not found")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
) -> Alert:
    actor = context.user.id
    try:
        alert = await alert_service.resolve_alert(session, tenant_id, str(alert_id), actor)
        await session.commit()
        return alert
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Alert not found")
        raise HTTPException(status_code=400, detail=str(e))
