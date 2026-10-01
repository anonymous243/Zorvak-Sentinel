import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.models import User, Tenant, Membership
from sentinel_core.schemas_human import UserCreate, UserResponse, OrganizationResponse, MembershipResponse, CurrentUserContext

def _load_jwt_secret() -> str:
    """
    Loads the JWT signing secret from the environment.

    Fails loudly at import time if JWT_SECRET is not configured.
    This prevents the application from starting with an insecure fallback.
    A predictable or hardcoded secret allows any party that knows the source
    code to forge valid session tokens.
    """
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET environment variable is not set. "
            "The application cannot start without a configured JWT signing secret. "
            "Set JWT_SECRET to a cryptographically random string of at least 32 characters."
        )
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET must be at least 32 characters long. "
            "The configured secret is too short to be secure."
        )
    return secret

JWT_SECRET: str = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

class AuthenticationError(Exception):
    pass

async def create_user_and_organization(session: AsyncSession, data: UserCreate) -> CurrentUserContext:
    # Check if email exists
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    # Hash password
    password_hash = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create User
    user = User(
        email=data.email,
        name=data.name,
        password_hash=password_hash,
    )
    session.add(user)
    await session.flush()

    # Create Organization (Tenant)
    tenant = Tenant(
        name=data.organization_name,
        slug=data.organization_name.lower().replace(" ", "-")
    )
    session.add(tenant)
    await session.flush()

    # Create Membership as OWNER
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role="OWNER"
    )
    session.add(membership)
    await session.commit()
    await session.refresh(user)
    await session.refresh(tenant)
    await session.refresh(membership)

    return CurrentUserContext(
        user=UserResponse.model_validate(user),
        memberships=[MembershipResponse.model_validate(membership)],
        organizations=[OrganizationResponse.model_validate(tenant)]
    )

from typing import Optional
from sentinel_core.security_event_service import (
    SYSTEM_TENANT_ID,
    SecurityEventCreate,
    persist_security_event,
)

_DUMMY_BCRYPT_HASH = "$2b$12$e8Y5t1mI/C3Yd5MvE6T2uO7YF5H0G3J8K1L9N2P4Q6R8S0T2U4V6W"

async def authenticate_human(
    session: AsyncSession,
    email: str,
    password: str,
    *,
    session_factory: Optional[any] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Side-channel mitigation: perform dummy bcrypt check to neutralize timing delta
        bcrypt.checkpw(password.encode('utf-8'), _DUMMY_BCRYPT_HASH.encode('utf-8'))
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=SYSTEM_TENANT_ID,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="unknown_user",
                metadata={
                    "auth_mechanism": "human_login",
                    "failure_category": "invalid_credentials",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("Invalid email or password")

    # Find trusted tenant for this user if available
    mem_result = await session.execute(select(Membership).where(Membership.user_id == user.id))
    m = mem_result.scalars().first()
    trusted_tenant_id = m.tenant_id if m else SYSTEM_TENANT_ID

    if user.status != "active":
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=trusted_tenant_id,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="inactive_user",
                metadata={
                    "auth_mechanism": "human_login",
                    "failure_category": "inactive_account",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("Invalid email or password")

    if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=trusted_tenant_id,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="invalid_password",
                metadata={
                    "auth_mechanism": "human_login",
                    "failure_category": "invalid_credentials",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("Invalid email or password")


    # Create JWT
    payload = {
        "sub": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

async def get_current_user_context(
    session: AsyncSession,
    token: str,
    *,
    session_factory: Optional[any] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> CurrentUserContext:
    now = datetime.now(timezone.utc)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=SYSTEM_TENANT_ID,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="expired_session",
                metadata={
                    "auth_mechanism": "human_jwt",
                    "failure_category": "expired_session",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("Invalid or expired session")
    except jwt.PyJWTError:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=SYSTEM_TENANT_ID,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="invalid_session",
                metadata={
                    "auth_mechanism": "human_jwt",
                    "failure_category": "invalid_session",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("Invalid or expired session")

    if not user_id:
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=SYSTEM_TENANT_ID,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="invalid_session",
                metadata={
                    "auth_mechanism": "human_jwt",
                    "failure_category": "missing_subject",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("Invalid session")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.status != "active":
        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=SYSTEM_TENANT_ID,
                event_type="AUTHENTICATION_FAILED",
                occurred_at=now,
                outcome="FAILURE",
                agent_id=None,
                request_id=request_id,
                correlation_id=correlation_id,
                reason_code="inactive_user" if user else "unknown_user",
                metadata={
                    "auth_mechanism": "human_jwt",
                    "failure_category": "inactive_account" if user else "unknown_user",
                },
            ),
            session_factory=session_factory,
            durable=True,
        )
        raise AuthenticationError("User account inactive")

    # Get memberships and organizations
    mem_result = await session.execute(select(Membership).where(Membership.user_id == user_id))
    memberships = mem_result.scalars().all()

    tenant_ids = [m.tenant_id for m in memberships]
    orgs = []
    if tenant_ids:
        org_result = await session.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        orgs = org_result.scalars().all()

    return CurrentUserContext(
        user=UserResponse.model_validate(user),
        memberships=[MembershipResponse.model_validate(m) for m in memberships],
        organizations=[OrganizationResponse.model_validate(o) for o in orgs]
    )

