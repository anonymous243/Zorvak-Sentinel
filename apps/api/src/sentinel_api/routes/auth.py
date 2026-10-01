from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel_core.database import get_session
from sentinel_core.schemas_human import UserCreate, UserLogin, CurrentUserContext
from sentinel_core.auth_service_human import (
    create_user_and_organization,
    authenticate_human,
    get_current_user_context,
    AuthenticationError,
)
# F-05: Import environment-aware cookie security flag.
# COOKIE_SECURE is True in any non-development environment, ensuring session
# tokens are never transmitted over plain HTTP in staging or production.
from sentinel_core.config import COOKIE_SECURE

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "sentinel_session"


def _set_session_cookie(response: Response, token: str) -> None:
    """
    Set the JWT session cookie with consistent, hardened attributes.

    - httponly: prevents JavaScript access (XSS mitigation)
    - samesite="lax": CSRF protection while allowing top-level navigations
    - secure: True in non-development environments (F-05 fix)
    - max_age: 24-hour rolling expiry
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=24 * 60 * 60,
    )


@router.post("/signup", response_model=CurrentUserContext, status_code=status.HTTP_201_CREATED)
async def signup(
    data: UserCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    try:
        context = await create_user_and_organization(session, data)
        token = await authenticate_human(session, data.email, data.password)
        _set_session_cookie(response, token)
        return context
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(
    data: UserLogin,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    try:
        token = await authenticate_human(session, data.email, data.password)
        _set_session_cookie(response, token)
        return {"status": "ok"}
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"status": "ok"}


@router.get("/me", response_model=CurrentUserContext)
async def get_me(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        context = await get_current_user_context(session, token)
        return context
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
