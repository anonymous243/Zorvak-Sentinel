from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import (
    Agent,
    ExternalIdentityProvider,
    AgentFederatedIdentity,
)


async def register_identity_provider(
    session: AsyncSession,
    tenant_id: str,
    name: str,
    provider_type: str,
    issuer_url: str,
    client_id: str,
) -> ExternalIdentityProvider:
    """
    Registers a new External Identity Provider for a tenant.
    """
    provider = ExternalIdentityProvider(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name=name,
        provider_type=provider_type,
        issuer_url=issuer_url,
        client_id=client_id,
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(provider)
    await session.flush()
    return provider


async def link_agent_to_federated_identity(
    session: AsyncSession,
    agent_id: str,
    provider_id: str,
    subject_id: str,
) -> AgentFederatedIdentity:
    """
    Binds a Sentinel agent to an external identity subject from a specific provider.
    """
    identity = AgentFederatedIdentity(
        id=str(uuid4()),
        agent_id=agent_id,
        provider_id=provider_id,
        subject_id=subject_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(identity)
    await session.flush()
    return identity


async def resolve_federated_agent(
    session: AsyncSession,
    tenant_id: str,
    issuer_url: str,
    subject_id: str,
) -> Agent | None:
    """
    Resolves an external JWT identity (issuer + subject) to an authoritative Sentinel Agent.
    """
    result = await session.execute(
        select(Agent)
        .join(AgentFederatedIdentity, Agent.id == AgentFederatedIdentity.agent_id)
        .join(ExternalIdentityProvider, AgentFederatedIdentity.provider_id == ExternalIdentityProvider.id)
        .where(ExternalIdentityProvider.tenant_id == tenant_id)
        .where(ExternalIdentityProvider.issuer_url == issuer_url)
        .where(ExternalIdentityProvider.status == "active")
        .where(AgentFederatedIdentity.subject_id == subject_id)
        .where(Agent.status == "active")
    )
    return result.scalar_one_or_none()
