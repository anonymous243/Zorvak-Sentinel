from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.agent_service import (
    create_agent,
    get_agent,
    list_agents,
)
from sentinel_core.database import get_session
from sentinel_core.schemas import AgentCreate, AgentResponse
from sentinel_api.routes.policies import router as policies_router
from sentinel_core.policy_service import PolicyValidationErrorException


app = FastAPI(
    title="ZORVAK SENTINEL",
    description="Security platform for autonomous AI agents.",
    version="0.1.0",
)

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


app.include_router(policies_router)


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
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    agent = await create_agent(session, data)
    return AgentResponse.model_validate(agent)


@app.get(
    "/agents",
    response_model=list[AgentResponse],
)
async def get_agents(
    session: AsyncSession = Depends(get_session),
) -> list[AgentResponse]:
    agents = await list_agents(session)
    return [AgentResponse.model_validate(agent) for agent in agents]


@app.get(
    "/agents/{agent_id}",
    response_model=AgentResponse,
)
async def get_agent_by_id(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> AgentResponse:
    agent = await get_agent(session, agent_id)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return AgentResponse.model_validate(agent)
