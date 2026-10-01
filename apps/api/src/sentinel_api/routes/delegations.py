from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.database import get_session
from sentinel_core.rbac import require_role
from sentinel_core.schemas_human import CurrentUserContext
from sentinel_core.models import AgentTrustRelationship, AgentDelegation
from sentinel_core import delegation_service

router = APIRouter(tags=["Multi-Agent Trust & Delegation"])


class TrustCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_agent_id: str = Field(min_length=1, max_length=36)
    trust_scope: dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrustResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    source_agent_id: str
    target_agent_id: str
    status: str
    trust_scope: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class DelegationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delegation_id: str = Field(min_length=1, max_length=36)
    delegator_agent_id: str = Field(min_length=1, max_length=36)
    delegate_agent_id: str = Field(min_length=1, max_length=36)
    action_scope: list[str] = Field(default_factory=list)
    resource_scope: list[str] = Field(default_factory=list)
    capability_scope: list[str] = Field(default_factory=list)
    issued_at: datetime
    expires_at: datetime
    signing_key_id: str = Field(min_length=1, max_length=36)
    signature: str = Field(min_length=1)
    parent_delegation_id: Optional[str] = None
    allow_transitive: bool = False
    request_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    delegator_agent_id: str
    delegate_agent_id: str
    trust_relationship_id: str
    action_scope: list[str]
    resource_scope: list[str]
    capability_scope: list[str]
    parent_delegation_id: Optional[str] = None
    status: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    signature: str
    signing_key_id: str
    request_id: Optional[str] = None
    created_at: datetime


# ============================================================================
# TRUST RELATIONSHIP ENDPOINTS
# ============================================================================

@router.post("/agents/{agent_id}/trust", response_model=TrustResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_trust(
    agent_id: str,
    body: TrustCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY"])),
) -> TrustResponse:
    try:
        trust = await delegation_service.create_trust_relationship(
            session=session,
            tenant_id=tenant_id,
            source_agent_id=agent_id,
            target_agent_id=body.target_agent_id,
            trust_scope=body.trust_scope,
            expires_at=body.expires_at,
            metadata=body.metadata,
        )
        return TrustResponse.model_validate(trust)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents/{agent_id}/trust", response_model=list[TrustResponse])
async def list_agent_trust(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY", "DEVELOPER", "VIEWER"])),
) -> list[TrustResponse]:
    query = (
        select(AgentTrustRelationship)
        .where(
            AgentTrustRelationship.tenant_id == tenant_id,
            AgentTrustRelationship.source_agent_id == agent_id,
        )
    )
    result = await session.execute(query)
    trusts = result.scalars().all()
    return [TrustResponse.model_validate(t) for t in trusts]


# ============================================================================
# DELEGATION ENDPOINTS
# ============================================================================

@router.post("/delegations", response_model=DelegationResponse, status_code=status.HTTP_201_CREATED)
async def create_delegation_endpoint(
    body: DelegationCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY"])),
) -> DelegationResponse:
    try:
        delegation = await delegation_service.create_delegation(
            session=session,
            tenant_id=tenant_id,
            delegation_id=body.delegation_id,
            delegator_agent_id=body.delegator_agent_id,
            delegate_agent_id=body.delegate_agent_id,
            action_scope=body.action_scope,
            resource_scope=body.resource_scope,
            capability_scope=body.capability_scope,
            issued_at=body.issued_at,
            expires_at=body.expires_at,
            signing_key_id=body.signing_key_id,
            signature=body.signature,
            parent_delegation_id=body.parent_delegation_id,
            allow_transitive=body.allow_transitive,
            request_id=body.request_id,
            metadata=body.metadata,
        )
        return DelegationResponse.model_validate(delegation)
    except ValueError as e:
        err_msg = str(e)
        if "scope violation" in err_msg.lower() or "authority" in err_msg.lower():
            raise HTTPException(status_code=403, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)


@router.get("/delegations", response_model=list[DelegationResponse])
async def list_delegations(
    delegator_agent_id: Optional[str] = Query(None),
    delegate_agent_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY", "DEVELOPER", "VIEWER"])),
) -> list[DelegationResponse]:
    query = select(AgentDelegation).where(AgentDelegation.tenant_id == tenant_id)
    if delegator_agent_id:
        query = query.where(AgentDelegation.delegator_agent_id == delegator_agent_id)
    if delegate_agent_id:
        query = query.where(AgentDelegation.delegate_agent_id == delegate_agent_id)
    if status_filter:
        query = query.where(AgentDelegation.status == status_filter)

    result = await session.execute(query)
    delegations = result.scalars().all()
    return [DelegationResponse.model_validate(d) for d in delegations]


@router.post("/delegations/{delegation_id}/revoke", response_model=DelegationResponse)
async def revoke_delegation_endpoint(
    delegation_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY"])),
) -> DelegationResponse:
    try:
        delegation = await delegation_service.revoke_delegation(
            session=session,
            tenant_id=tenant_id,
            delegation_id=delegation_id,
        )
        return DelegationResponse.model_validate(delegation)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
