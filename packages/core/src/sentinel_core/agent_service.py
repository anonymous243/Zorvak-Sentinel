from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import Agent
from sentinel_core.schemas import AgentCreate


async def create_agent(
    session: AsyncSession,
    data: AgentCreate,
    tenant_id: str,
) -> Agent:
    """
    Create a new Agent belonging to the given tenant.

    The ``tenant_id`` parameter is mandatory and must come from an
    authoritative authenticated principal — never from unverified request
    body data.  Making it an explicit positional argument ensures accidental
    tenant-less creation raises a TypeError rather than silently producing a
    NULL tenant_id in the database.
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required and must not be empty")

    agent = Agent(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        provider=data.provider,
        external_id=data.external_id,
        environment=data.environment,
    )

    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    return agent


async def list_agents(
    session: AsyncSession,
    tenant_id: str,
) -> list[Agent]:
    """
    Return only agents belonging to the given tenant.

    The ``tenant_id`` must come from an authenticated principal.
    """
    result = await session.execute(
        select(Agent)
        .where(Agent.tenant_id == tenant_id)
        .order_by(Agent.created_at.desc())
    )
    return list(result.scalars().all())


async def get_agent(
    session: AsyncSession,
    agent_id: str,
    tenant_id: str,
) -> Agent | None:
    """
    Fetch a single agent by ID, scoped to the given tenant.

    Returns None if the agent does not exist or belongs to a different
    tenant.  Callers must not reveal to unauthenticated parties whether
    an agent exists in another tenant (respond 404, not 403).
    """
    result = await session.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()
