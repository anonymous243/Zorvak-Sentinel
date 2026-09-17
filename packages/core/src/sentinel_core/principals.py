from pydantic import BaseModel, Field

class AuthenticatedPrincipal(BaseModel):
    """
    Represents a verified, authenticated principal within the system.
    This is strictly created by the authentication service and must never
    be constructed directly from unverified caller input.
    """
    tenant_id: str = Field(..., min_length=1, max_length=36)
    agent_id: str = Field(..., min_length=1, max_length=36)
    credential_id: str = Field(..., min_length=1, max_length=36)
