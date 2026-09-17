from datetime import datetime, timezone

import bcrypt
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import Agent, AgentCredential, Tenant
from sentinel_core.principals import AuthenticatedPrincipal


class AuthenticationError(Exception):
    """Raised when authentication fails for any reason."""
    pass


async def authenticate_agent(
    session: AsyncSession,
    agent_id: str,
    secret: SecretStr
) -> AuthenticatedPrincipal:
    """
    Authenticates an agent given their stable agent_id and a secret credential.
    
    This function implements a strict fail-closed boundary. It returns an
    AuthenticatedPrincipal only if:
    - The agent exists and is active.
    - The agent's tenant exists and is active.
    - An active credential exists for the agent.
    - The provided secret matches the bcrypt hash of the active credential.
    - The credential has not expired.
    
    Any failure immediately raises AuthenticationError.
    """
    # 1. Fetch Agent and Tenant
    agent_stmt = select(Agent, Tenant).join(Tenant, Agent.tenant_id == Tenant.id).where(Agent.id == agent_id)
    result = await session.execute(agent_stmt)
    row = result.first()
    
    if not row:
        raise AuthenticationError("Authentication failed")
        
    agent, tenant = row
    
    if agent.status != "active":
        raise AuthenticationError("Authentication failed")
        
    if tenant.status != "active":
        raise AuthenticationError("Authentication failed")
        
    # 2. Fetch Active Credentials
    now = datetime.now(timezone.utc)
    cred_stmt = select(AgentCredential).where(
        AgentCredential.agent_id == agent_id,
        AgentCredential.status == "active"
    )
    result = await session.execute(cred_stmt)
    credentials = result.scalars().all()
    
    if not credentials:
        raise AuthenticationError("Authentication failed")
        
    # 3. Verify Secret against Hashes
    valid_credential = None
    provided_secret = secret.get_secret_value().encode("utf-8")
    
    for cred in credentials:
        # Check expiration
        if cred.expires_at and cred.expires_at < now:
            continue
            
        # bcrypt checkpw does a safe constant-time string comparison
        if bcrypt.checkpw(provided_secret, cred.secret_hash.encode("utf-8")):
            valid_credential = cred
            break
            
    if not valid_credential:
        raise AuthenticationError("Authentication failed")
        
    # 4. Update last_used_at
    valid_credential.last_used_at = now
    
    from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
    
    await persist_security_event(session, SecurityEventCreate(
        tenant_id=agent.tenant_id,
        event_type="AUTHENTICATION_SUCCESS",
        occurred_at=now,
        outcome="SUCCESS",
        agent_id=agent.id,
        credential_id=valid_credential.id,
    ))
    
    # 5. Return Principal
    return AuthenticatedPrincipal(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        credential_id=valid_credential.id
    )
