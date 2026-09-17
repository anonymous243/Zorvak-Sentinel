from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import Agent
from sentinel_core.schemas import AgentCreate


async def create_agent(
    session: AsyncSession,
    data: AgentCreate,
) -> Agent:
    agent = Agent(
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
) -> list[Agent]:
    result = await session.execute(
        select(Agent).order_by(Agent.created_at.desc())
    )

    return list(result.scalars().all())


async def get_agent(
    session: AsyncSession,
    agent_id: str,
) -> Agent | None:
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )

    return result.scalar_one_or_none()
