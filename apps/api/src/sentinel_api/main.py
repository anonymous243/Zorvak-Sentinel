from fastapi import Depends, FastAPI, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.agent_service import (
    create_agent,
    get_agent,
    list_agents,
)
from sentinel_core.database import get_session
from sentinel_core.schemas import AgentCreate, AgentResponse
from sentinel_api.routes.policies import router as policies_router
from sentinel_api.routes.auth import router as auth_router
from sentinel_core.policy_service import PolicyValidationErrorException
from sentinel_core.rbac import get_current_user, require_role
from sentinel_core.schemas_human import CurrentUserContext



import uuid
import time
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Size Limit
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            return Response("Request body too large", status_code=413)
        
        # 2. Observability correlation
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        response = await call_next(request)
        
        # 3. Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Correlation-ID"] = request_id
        
        return response



app = FastAPI(
    title="ZORVAK SENTINEL",
    description="Security platform for autonomous AI agents.",
    version="0.1.0",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from sentinel_core.request_signing import RequestReplayError

@app.exception_handler(PolicyValidationErrorException)
async def policy_validation_exception_handler(request: Request, exc: PolicyValidationErrorException):
    errors = [
        {"code": error.code, "message": error.message, "field": error.field}
        for error in exc.result.errors
    ]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Policy validation failed", "errors": errors},
    )

@app.exception_handler(RequestReplayError)
async def request_replay_exception_handler(request: Request, exc: RequestReplayError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
    )


app.include_router(policies_router)
app.include_router(auth_router)
from sentinel_api.routes.alerts import router as alerts_router
app.include_router(alerts_router)
from sentinel_api.routes.evidence import router as evidence_router
app.include_router(evidence_router)
from sentinel_api.routes.investigations import router as investigations_router
app.include_router(investigations_router)
from sentinel_api.routes.analytics import router as analytics_router
app.include_router(analytics_router)
from sentinel_api.routes.ai_security import router as ai_security_router
app.include_router(ai_security_router)
from sentinel_api.routes.delegations import router as delegations_router
app.include_router(delegations_router)
from sqlalchemy import text

@app.get("/ready")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database not ready")

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent(
    data: AgentCreate,
    # F-01: Require authenticated human with OWNER or ADMIN role.
    # require_role() enforces X-Tenant-ID presence and validates the
    # user's membership in that exact tenant.
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN"])),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    # tenant_id is already validated against the authenticated user's
    # membership inside require_role(). We use it directly as the
    # authoritative tenant for the new agent.
    agent = await create_agent(session, data, tenant_id=tenant_id)
    return AgentResponse.model_validate(agent)


@app.get(
    "/agents",
    response_model=list[AgentResponse],
)
async def get_agents(
    # F-01: Require authenticated human. Any active membership role can
    # list agents within their own tenant.
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY", "DEVELOPER", "VIEWER"])),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> list[AgentResponse]:
    # Return only agents belonging to the authenticated tenant.
    agents = await list_agents(session, tenant_id=tenant_id)
    return [AgentResponse.model_validate(agent) for agent in agents]


@app.get(
    "/agents/{agent_id}",
    response_model=AgentResponse,
)
async def get_agent_by_id(
    agent_id: str,
    # F-01: Require authenticated human.
    context: CurrentUserContext = Depends(require_role(["OWNER", "ADMIN", "SECURITY", "DEVELOPER", "VIEWER"])),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    # Fetch by agent_id AND tenant_id — never by agent_id alone.
    # If the agent belongs to a different tenant, this returns None,
    # and we respond 404 to avoid leaking cross-tenant existence.
    agent = await get_agent(session, agent_id, tenant_id=tenant_id)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return AgentResponse.model_validate(agent)
