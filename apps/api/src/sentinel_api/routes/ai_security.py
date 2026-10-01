from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sentinel_core.database import get_session
from sentinel_core.rbac import get_current_user, require_role
from sentinel_core.schemas_human import CurrentUserContext
from sentinel_core.ai_security_plane import disable_agent, contain_agent, AIControlPlaneException
from sentinel_core.models import Agent
from sqlalchemy import select

router = APIRouter(prefix="/ai-security", tags=["ai-security"])

@router.post("/kill-switch/{agent_id}")
async def kill_switch(
    agent_id: str,
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY"])),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
):
    """Human-gated kill switch."""
    try:
        await disable_agent(session, tenant_id, agent_id)
        return {"status": "disabled"}
    except AIControlPlaneException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/contain/{agent_id}")
async def contain(
    agent_id: str,
    reason: str,
    # This might be called internally or by a system role. 
    # Let's allow OWNER/ADMIN/SECURITY for manual containment as well, 
    # but autonomous containment happens within the backend logic.
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY"])),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
):
    try:
        await contain_agent(session, tenant_id, agent_id, reason)
        return {"status": "contained"}
    except AIControlPlaneException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

