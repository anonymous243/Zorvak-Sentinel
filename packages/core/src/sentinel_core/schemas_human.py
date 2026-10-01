from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8)
    organization_name: str = Field(min_length=1, max_length=255)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str | None
    status: str
    created_at: datetime

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str
    status: str
    created_at: datetime

class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    tenant_id: str
    role: str
    status: str
    created_at: datetime

class CurrentUserContext(BaseModel):
    user: UserResponse
    memberships: list[MembershipResponse]
    organizations: list[OrganizationResponse]
