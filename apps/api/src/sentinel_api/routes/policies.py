from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.database import get_session
from sentinel_core.policy_service import create_policy, list_policies
from sentinel_core.schemas import PolicyCreate, PolicyResponse
from sentinel_core.principals import AuthenticatedPrincipal
from fastapi import HTTPException


router = APIRouter(
    prefix="/policies",
    tags=["policies"],
)

from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import SecretStr
from sentinel_core.authentication_service import authenticate_agent, AuthenticationError

security = HTTPBasic()

async def get_current_principal(
    credentials: HTTPBasicCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> AuthenticatedPrincipal:
    try:
        return await authenticate_agent(session, credentials.username, SecretStr(credentials.password))
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Authentication failed")


from fastapi import Header
@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_policy(
    data: PolicyCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    if tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="X-Tenant-ID mismatch")
    policy = await create_policy(session, principal, data)
    return PolicyResponse.model_validate(policy)


@router.get(
    "",
    response_model=list[PolicyResponse],
)
async def get_policies(
    session: AsyncSession = Depends(get_session),
) -> list[PolicyResponse]:
    policies = await list_policies(session)
    return [PolicyResponse.model_validate(policy) for policy in policies]

from sentinel_core.schemas import ConflictReport
from sentinel_core.conflict_analyzer import analyze_conflicts
from fastapi import HTTPException
from sqlalchemy import select
from sentinel_core.models import PolicyVersion

@router.post(
    "/{policy_id}/versions/{version_id}/analyze",
    response_model=list[ConflictReport],
)
async def analyze_policy_conflicts_endpoint(
    policy_id: str,
    version_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> list[ConflictReport]:
    # 1. Load target version
    target_result = await session.execute(
        select(PolicyVersion).where(
            PolicyVersion.id == version_id,
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.tenant_id == tenant_id,
        )
    )
    target = target_result.scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Target policy version not found")

    # 2. Load all active versions in tenant
    active_result = await session.execute(
        select(PolicyVersion).where(
            PolicyVersion.tenant_id == tenant_id,
            PolicyVersion.status == "active",
        )
    )
    active_versions = list(active_result.scalars().all())

    # 3. Analyze
    try:
        reports = analyze_conflicts(target, active_versions)
        return reports
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import SecretStr
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.authentication_service import authenticate_agent, AuthenticationError

security = HTTPBasic()

async def get_current_principal( # defined below
    credentials: HTTPBasicCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> AuthenticatedPrincipal:
    try:
        return await authenticate_agent(session, credentials.username, SecretStr(credentials.password))
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Authentication failed")

from typing import Optional
from sentinel_core.schemas import PolicySimulationRequest, PolicySimulationResult, PolicyRollbackRequest, PolicyRollbackResult
from sentinel_core.models import Agent, Policy, PolicyVersion
from sentinel_core.capability_service import check_capability
from sentinel_core.risk import DummyBehaviorSignalProvider
from sentinel_core.risk_engine import evaluate_risk
from sentinel_core.authorization import ActionRequest
from sentinel_core.policy_simulator import simulate_authorization
from sqlalchemy.orm import selectinload

@router.post(
    "/simulate",
    response_model=PolicySimulationResult,
    status_code=status.HTTP_200_OK,
)
async def simulate_authorization_endpoint(
    request_data: PolicySimulationRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> PolicySimulationResult:
    
    # 1. Tenant Check
    if tenant_id and tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="X-Tenant-ID mismatch")
        
    # 2. Database loading: Agent
    agent_result = await session.execute(
        select(Agent).where(Agent.id == request_data.agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    agent_status = agent.status if agent else None
    
    # 3. Database loading: Capability (Pure evaluation)
    cap_result = await check_capability(
        session, principal, request_data.tool_id, request_data.action, request_data.resource
    )
    
    # 4. Database loading: Policies
    policy_result = await session.execute(
        select(Policy)
        .options(selectinload(Policy.active_version))
        .where(Policy.tenant_id == principal.tenant_id)
        .where(Policy.enabled.is_(True))
    )
    db_policies = list(policy_result.scalars().all())
    
    # Validate DB state integrity
    for p in db_policies:
        if p.active_version_id and not p.active_version:
            raise HTTPException(status_code=500, detail="Inconsistent active policy state")
        if p.active_version and p.active_version.tenant_id != principal.tenant_id:
            raise HTTPException(status_code=500, detail="Cross-tenant active version in DB")
            
    # Prepare hypothetical set
    hypothetical_policies = []
    candidate_used = False
    
    if request_data.candidate_policy_version_id:
        cand_result = await session.execute(
            select(PolicyVersion).where(
                PolicyVersion.id == request_data.candidate_policy_version_id,
                PolicyVersion.tenant_id == principal.tenant_id
            )
        )
        candidate = cand_result.scalars().first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate version not found or wrong tenant")
        
        # Load the candidate's parent policy to ensure we replace its active version properly
        cand_policy_result = await session.execute(
            select(Policy).where(Policy.id == candidate.policy_id, Policy.tenant_id == principal.tenant_id)
        )
        cand_policy = cand_policy_result.scalars().first()
        if not cand_policy:
            raise HTTPException(status_code=404, detail="Candidate belongs to an unknown policy")
            
        candidate_used = True
        
        # Build completely detached copy of candidate's policy
        # so we do not mutate ORM
        hypothetical_candidate_policy = Policy(
            id=cand_policy.id,
            tenant_id=cand_policy.tenant_id,
            name=cand_policy.name,
            enabled=cand_policy.enabled,
            active_version=PolicyVersion(
                id=candidate.id,
                policy_id=candidate.policy_id,
                tenant_id=candidate.tenant_id,
                version=candidate.version,
                status="active", # Simulated activation
                effect=candidate.effect,
                priority=candidate.priority,
                action=candidate.action,
                resource=candidate.resource
            )
        )
        hypothetical_policies.append(hypothetical_candidate_policy)
        
        # Add remaining DB policies, explicitly skipping the one we just replaced
        for p in db_policies:
            if p.id != cand_policy.id:
                # Still pass as a detached copy for immutability invariant
                if p.active_version:
                    detached_version = PolicyVersion(
                        id=p.active_version.id,
                        policy_id=p.active_version.policy_id,
                        tenant_id=p.active_version.tenant_id,
                        version=p.active_version.version,
                        status=p.active_version.status,
                        effect=p.active_version.effect,
                        priority=p.active_version.priority,
                        action=p.active_version.action,
                        resource=p.active_version.resource
                    )
                else:
                    detached_version = None
                    
                detached_p = Policy(
                    id=p.id,
                    tenant_id=p.tenant_id,
                    name=p.name,
                    enabled=p.enabled,
                    active_version=detached_version
                )
                hypothetical_policies.append(detached_p)
                
    else:
        # Standard pure current-state simulation
        for p in db_policies:
            if p.active_version:
                detached_version = PolicyVersion(
                    id=p.active_version.id,
                    policy_id=p.active_version.policy_id,
                    tenant_id=p.active_version.tenant_id,
                    version=p.active_version.version,
                    status=p.active_version.status,
                    effect=p.active_version.effect,
                    priority=p.active_version.priority,
                    action=p.active_version.action,
                    resource=p.active_version.resource
                )
            else:
                detached_version = None
                
            detached_p = Policy(
                id=p.id,
                tenant_id=p.tenant_id,
                name=p.name,
                enabled=p.enabled,
                active_version=detached_version
            )
            hypothetical_policies.append(detached_p)
            
    # 5. Build pure ActionRequest
    action_request = ActionRequest(
        agent_id=request_data.agent_id,
        tool_id=request_data.tool_id,
        action=request_data.action,
        resource=request_data.resource,
        context=request_data.context
    )
    
    # 6. Evaluate Risk (Pure evaluation)
    provider = DummyBehaviorSignalProvider()
    risk_assessment = await evaluate_risk(action_request, principal, provider)
    
    # 7. Execute pure simulation core
    return simulate_authorization(
        request=action_request,
        principal=principal,
        policies=hypothetical_policies,
        agent_status=agent_status,
        capability_allowed=cap_result.allowed,
        capability_id=cap_result.capability_id,
        capability_reason=cap_result.reason,
        risk_assessment=risk_assessment,
        candidate_used=candidate_used
    )

from sentinel_core.policy_service import rollback_policy, PolicyValidationErrorException, PolicyConcurrencyException

@router.post(
    "/{policy_id}/rollback",
    response_model=PolicyRollbackResult,
    status_code=status.HTTP_200_OK,
)
async def rollback_policy_endpoint(
    policy_id: str,
    request_data: PolicyRollbackRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> PolicyRollbackResult:
    if tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="X-Tenant-ID mismatch")
        
    try:
        result = await rollback_policy(session, principal, policy_id, request_data.target_version_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PolicyValidationErrorException as e:
        raise HTTPException(status_code=400, detail="Target version validation failed")
    except PolicyConcurrencyException:
        raise HTTPException(status_code=409, detail="Policy state changed concurrently; retry the operation.")


from sentinel_core.schemas import PolicyAuditResponse
from sentinel_core.models import PolicyAuditRecord

@router.get(
    "/{policy_id}/audit",
    response_model=list[PolicyAuditResponse],
)
async def get_policy_audit(
    policy_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> list[PolicyAuditResponse]:
    if tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="X-Tenant-ID mismatch")
        
    result = await session.execute(
        select(PolicyAuditRecord)
        .where(
            PolicyAuditRecord.tenant_id == principal.tenant_id,
            PolicyAuditRecord.policy_id == policy_id
        )
        .order_by(PolicyAuditRecord.occurred_at.asc(), PolicyAuditRecord.id.asc())
    )
    audits = result.scalars().all()
    return [PolicyAuditResponse.model_validate(audit) for audit in audits]

