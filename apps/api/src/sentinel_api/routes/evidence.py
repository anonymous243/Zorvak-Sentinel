from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.database import get_session
from sentinel_core.schemas import EvidenceResponse
from sentinel_core.schemas_human import CurrentUserContext
from sentinel_core.rbac import require_role
from sentinel_core import evidence_service

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.get("", response_model=List[EvidenceResponse])
async def list_evidence(
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
    incident_id: UUID | None = Query(None),
    evidence_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[EvidenceResponse]:
    """
    List evidence securely. Tenant isolation is strictly enforced.
    """
    records = await evidence_service.list_evidence(
        session,
        tenant_id=tenant_id,
        incident_id=str(incident_id) if incident_id else None,
        evidence_type=evidence_type,
        limit=limit,
        offset=offset
    )
    return records

@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["SECURITY", "ADMIN"])),
) -> EvidenceResponse:
    """
    Get a single evidence record by ID securely.
    """
    record = await evidence_service.get_evidence(session, tenant_id, str(evidence_id))
    if not record:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return record
