from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.core.security import get_current_user, user_has_role
from app.models.user import User

audit_logger = logging.getLogger("app.audit")


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def audit_event(
    action: str,
    *,
    actor: str | None = None,
    status_value: str = "success",
    request: Request | None = None,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {
        "action": action,
        "status": status_value,
        "actor": actor or "system",
    }
    if request is not None:
        payload["method"] = request.method
        payload["path"] = request.url.path
        payload["ip"] = _client_ip(request)
    payload.update({key: value for key, value in fields.items() if value is not None})
    message = " ".join(f"{key}={value}" for key, value in payload.items())
    audit_logger.info("AUDIT %s", message)


async def require_admin_access(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    if not user_has_role(current_user.role, "admin"):
        audit_event(
            "admin_route_denied",
            actor=current_user.email,
            status_value="denied",
            request=request,
            required_role="admin",
            role=current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role required.",
        )

    audit_event(
        "admin_route_access",
        actor=current_user.email,
        request=request,
        role=current_user.role,
    )
    return current_user
