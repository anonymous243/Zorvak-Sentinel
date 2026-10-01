from typing import List
from fastapi import Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sentinel_core.database import get_session
from sentinel_core.auth_service_human import get_current_user_context, AuthenticationError
from sentinel_core.schemas_human import CurrentUserContext

COOKIE_NAME = "sentinel_session"


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> CurrentUserContext:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        context = await get_current_user_context(session, token)
        return context
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


def require_role(roles: List[str]):
    """
    RBAC dependency that requires:
      1. An authenticated human session (JWT cookie).
      2. An explicit X-Tenant-ID header identifying the target tenant.
      3. The authenticated user must have an *active* membership in that
         specific tenant with one of the required roles.

    Security invariants:
      - A missing X-Tenant-ID is treated as a bad request (400), NOT as
        "any tenant". Omitting the header can never grant cross-tenant access.
      - A role held in Tenant A cannot authorize actions in Tenant B.
      - Only active memberships are accepted.
    """
    async def role_checker(
        request: Request,
        tenant_id: str = Header(..., alias="X-Tenant-ID"),
        context: CurrentUserContext = Depends(get_current_user),
    ) -> CurrentUserContext:
        # tenant_id is required by the Header dependency above.
        # FastAPI will return 422 before we even reach here if it is absent,
        # but we add an explicit guard for clarity and defense-in-depth.
        if not tenant_id or not tenant_id.strip():
            raise HTTPException(
                status_code=400,
                detail="X-Tenant-ID header is required for this operation."
            )

        # Find the authenticated user's membership in the exact requested tenant.
        matched_membership = None
        for membership in context.memberships:
            if membership.tenant_id == tenant_id:
                matched_membership = membership
                break

        if matched_membership is None:
            # The user does not belong to this tenant at all. Respond 403
            # so we do not reveal whether the tenant exists.
            raise HTTPException(
                status_code=403,
                detail="Access denied: you are not a member of the requested organization."
            )

        if matched_membership.status != "active":
            raise HTTPException(
                status_code=403,
                detail="Access denied: your membership in this organization is not active."
            )

        if matched_membership.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Access denied: this operation requires one of the following "
                    f"roles: {', '.join(roles)}."
                )
            )

        return context

    return role_checker
