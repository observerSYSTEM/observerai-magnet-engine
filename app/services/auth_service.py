from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit_event
from app.core.config import Settings
from app.core.security import hash_password, normalize_email, verify_password
from app.models.user import User
from app.schemas.auth import RoleName


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == normalize_email(email))
    return db.scalar(stmt)


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: RoleName = "viewer",
    is_active: bool = True,
) -> User:
    normalized_email = normalize_email(email)
    existing = get_user_by_email(db, normalized_email)
    if existing is not None:
        raise ValueError(f"User already exists: {normalized_email}")

    row = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def assign_user_role(
    db: Session,
    *,
    email: str,
    role: RoleName,
    changed_by: str | None = None,
) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None
    previous_role = user.role
    if previous_role == role:
        return user
    user.role = role
    db.commit()
    db.refresh(user)
    audit_event(
        "role_assignment_change",
        actor=changed_by or "system",
        target_email=user.email,
        previous_role=previous_role,
        new_role=role,
    )
    return user


def ensure_operator_user(db: Session, settings: Settings) -> User | None:
    """
    Seed or promote the primary operator account from environment settings.

    This provides a deterministic first-admin path for production bootstrap.
    """

    if not settings.operator_email or not settings.operator_password:
        return None

    normalized_email = normalize_email(settings.operator_email)
    user = get_user_by_email(db, normalized_email)
    if user is None:
        created_user = create_user(
            db,
            email=normalized_email,
            password=settings.operator_password,
            role=settings.operator_role,
            is_active=True,
        )
        audit_event(
            "operator_bootstrap_created",
            actor="bootstrap",
            target_email=created_user.email,
            new_role=created_user.role,
        )
        return created_user

    changed = False
    previous_role = user.role
    if user.role != settings.operator_role:
        user.role = settings.operator_role
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True

    if changed:
        db.commit()
        db.refresh(user)
        if previous_role != user.role:
            audit_event(
                "role_assignment_change",
                actor="bootstrap",
                target_email=user.email,
                previous_role=previous_role,
                new_role=user.role,
            )
        if user.is_active:
            audit_event(
                "operator_bootstrap_updated",
                actor="bootstrap",
                target_email=user.email,
                role=user.role,
            )

    if not verify_password(settings.operator_password, user.password_hash):
        audit_event(
            "operator_bootstrap_password_preserved",
            actor="bootstrap",
            status_value="skipped",
            target_email=user.email,
        )

    return user
