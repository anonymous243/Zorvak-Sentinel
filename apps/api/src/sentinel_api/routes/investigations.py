from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sentinel_core.database import get_session
from sentinel_core.schemas import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationStatusTransition,
    InvestigationNoteCreate,
    InvestigationNoteResponse,
    InvestigationFindingCreate,
    InvestigationFindingResponse
)
from sentinel_core.schemas_human import CurrentUserContext
from sentinel_core.rbac import require_role
from sentinel_core import investigation_service
from sentinel_core.models import Investigation

router = APIRouter(prefix="/investigations", tags=["Investigations"])

@router.post("", response_model=InvestigationResponse)
async def create_investigation(
    req: InvestigationCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> InvestigationResponse:
    try:
        inv = await investigation_service.create_investigation(
            session=session,
            tenant_id=tenant_id,
            incident_id=req.incident_id,
            title=req.title,
            actor_id=context.user.id,
            summary=req.summary,
            severity=req.severity,
            assigned_to=req.assigned_to
        )
        return inv
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[InvestigationResponse])
async def list_investigations(
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
    status: str | None = Query(None),
    incident_id: str | None = Query(None)
) -> List[InvestigationResponse]:
    stmt = select(Investigation).where(Investigation.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Investigation.status == status)
    if incident_id:
        stmt = stmt.where(Investigation.incident_id == incident_id)
        
    result = await session.execute(stmt)
    return list(result.scalars().all())

@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> InvestigationResponse:
    inv = await investigation_service.get_investigation(session, tenant_id, str(investigation_id))
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv

@router.post("/{investigation_id}/transition", response_model=InvestigationResponse)
async def transition_investigation(
    investigation_id: UUID,
    req: InvestigationStatusTransition,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> InvestigationResponse:
    try:
        inv = await investigation_service.transition_investigation(
            session=session,
            tenant_id=tenant_id,
            investigation_id=str(investigation_id),
            status=req.status,
            actor_id=context.user.id,
            reason=req.reason
        )
        return inv
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{investigation_id}/notes", response_model=InvestigationNoteResponse)
async def add_investigation_note(
    investigation_id: UUID,
    req: InvestigationNoteCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> InvestigationNoteResponse:
    try:
        note = await investigation_service.add_investigation_note(
            session=session,
            tenant_id=tenant_id,
            investigation_id=str(investigation_id),
            content=req.content,
            author_id=context.user.id
        )
        return note
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{investigation_id}/notes", response_model=List[InvestigationNoteResponse])
async def list_investigation_notes(
    investigation_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> List[InvestigationNoteResponse]:
    notes = await investigation_service.list_investigation_notes(session, tenant_id, str(investigation_id))
    return notes

@router.post("/{investigation_id}/findings", response_model=InvestigationFindingResponse)
async def add_investigation_finding(
    investigation_id: UUID,
    req: InvestigationFindingCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> InvestigationFindingResponse:
    try:
        finding = await investigation_service.add_investigation_finding(
            session=session,
            tenant_id=tenant_id,
            investigation_id=str(investigation_id),
            title=req.title,
            description=req.description,
            severity=req.severity,
            status=req.status,
            created_by=context.user.id
        )
        return finding
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{investigation_id}/findings", response_model=List[InvestigationFindingResponse])
async def list_investigation_findings(
    investigation_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> List[InvestigationFindingResponse]:
    findings = await investigation_service.list_investigation_findings(session, tenant_id, str(investigation_id))
    return findings

@router.get("/{investigation_id}/timeline")
async def get_investigation_timeline(
    investigation_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"]))
) -> List[Dict[str, Any]]:
    try:
        timeline = await investigation_service.get_investigation_timeline(session, tenant_id, str(investigation_id))
        return timeline
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
