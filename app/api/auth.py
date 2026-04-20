import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit import audit_event
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthUserOut, LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_login", limit=5, window_seconds=60))],
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    if user is None:
        logger.warning(
            "Authentication failed | email=%s ip=%s",
            payload.email.strip().lower(),
            request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.role == "admin":
        audit_event(
            "admin_login",
            actor=user.email,
            request=request,
            role=user.role,
        )

    return TokenResponse(access_token=create_access_token(user=user), role=user.role)


@router.get(
    "/me",
    response_model=AuthUserOut,
    dependencies=[Depends(rate_limit("auth_me", limit=60, window_seconds=60))],
)
def get_me(current_user: User = Depends(get_current_user)) -> AuthUserOut:
    return AuthUserOut.model_validate(current_user)
