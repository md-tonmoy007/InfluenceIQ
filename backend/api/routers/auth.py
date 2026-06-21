from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.api.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    UserResponse,
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
        user=UserResponse(
            user_id=user.id,
            email=user.email,
            name=user.name,
            company_name=user.company_name,
        ),
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

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    _set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        user=UserResponse(
            user_id=user.id,
            email=user.email,
            name=user.name,
            company_name=user.company_name,
        ),
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
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        company_name=current_user.company_name,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, response: Response) -> RefreshResponse:
    """Exchange a valid refresh token for a new access token."""
    payload_data = decode_token(payload.refresh_token)

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
