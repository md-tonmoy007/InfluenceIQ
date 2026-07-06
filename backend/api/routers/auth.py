from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.api.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    UserResponse,
)
from backend.api.schemas.settings import (
    ChangePasswordRequest,
    UpdateProfileRequest,
)
from backend.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.core.config import settings
from backend.core.database.models import User
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly cookies for access and refresh tokens."""
    access_max_age = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    refresh_max_age = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=access_max_age,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=refresh_max_age,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies."""
    response.set_cookie(
        key="access_token", value="", httponly=True, samesite="lax", max_age=0, path="/"
    )
    response.set_cookie(
        key="refresh_token", value="", httponly=True, samesite="lax", max_age=0, path="/"
    )


def _user_to_response(user: User) -> UserResponse:
    """Map a ``User`` ORM row to the :class:`UserResponse` shape."""
    return UserResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        company_name=user.company_name,
        role=user.role,
        timezone=user.timezone,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest, response: Response, db: Session = Depends(get_db)
) -> AuthResponse:
    """Create a new user account."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        company_name=payload.company_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    _set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        user=_user_to_response(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate a user and return tokens."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.deleted_at is not None:
        # Soft-deleted accounts cannot log back in; surface a generic
        # 401 to avoid leaking which email is soft-deleted.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    _set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        user=_user_to_response(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Log out the current user by clearing auth cookies."""
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return _user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Partial update of the current user's profile (name / role / timezone)."""
    if payload.name is not None:
        current_user.name = payload.name
    if payload.role is not None:
        current_user.role = payload.role
    if payload.timezone is not None:
        current_user.timezone = payload.timezone

    db.commit()
    db.refresh(current_user)
    return _user_to_response(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Change the current user's password.

    Requires the current password to confirm ownership. The new
    password is stored as a bcrypt hash (same scheme as signup).
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Soft-delete the current user's account.

    Sets ``User.deleted_at = utcnow()`` and clears the auth cookies.
    The row is retained so any data tied to the user (campaigns,
    brand profile, etc.) is preserved; the user simply cannot
    authenticate again. ``get_current_user`` filters on
    ``deleted_at IS NULL`` to enforce this.
    """
    current_user.deleted_at = datetime.now(UTC)
    db.commit()
    _clear_auth_cookies(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    response: Response,
    payload: RefreshRequest | None = None,
    refresh_token: str | None = Cookie(default=None),
) -> RefreshResponse:
    """Exchange a valid refresh token for a new access token.

    Accepts the refresh token from the JSON body, or falls back to
    the ``refresh_token`` HttpOnly cookie so that a page reload does
    not break token renewal.
    """
    token_value = (
        payload.refresh_token
        if payload and payload.refresh_token
        else refresh_token
    )
    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required",
        )

    payload_data = decode_token(token_value)

    if payload_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected refresh token",
        )

    user_id = payload_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return RefreshResponse(access_token=new_access_token)
