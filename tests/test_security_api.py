import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.api.auth import login
from app.core.config import DEFAULT_AUTH_JWT_SECRET, Settings
from app.core.rate_limit import clear_rate_limit_state, rate_limit
from app.core.security import create_access_token, get_current_user, require_admin, verify_password
from app.db.base import Base
from app.schemas.auth import LoginRequest
from app.services.auth_service import create_user, ensure_operator_user, get_user_by_email


def _build_test_db():
    db_dir = Path("F:/observerai-magnet-engine/.tmp-test-dbs")
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"observerai-security-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return db_path, engine, testing_session_local


def _cleanup_test_db(db_path: Path, engine) -> None:
    engine.dispose()
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass


def _request_with_ip(ip_address: str) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/auth/login",
        "headers": [(b"x-forwarded-for", ip_address.encode("utf-8"))],
        "client": (ip_address, 12345),
    }
    return Request(scope)


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


def test_admin_only_route_blocked_for_non_admin_and_allowed_for_admin():
    clear_rate_limit_state()
    db_path, engine, testing_session_local = _build_test_db()

    try:
        with testing_session_local() as db:
            viewer = create_user(
                db,
                email="viewer@example.com",
                password="viewer-pass-123",
                role="viewer",
            )
            admin = create_user(
                db,
                email="admin@example.com",
                password="admin-pass-123",
                role="admin",
            )

            guard = require_admin()

            try:
                asyncio.run(guard(current_user=viewer))
                raise AssertionError("Viewer should not pass the admin guard.")
            except HTTPException as exc:
                assert exc.status_code == 403

            granted = asyncio.run(guard(current_user=admin))
            assert granted.role == "admin"
    finally:
        clear_rate_limit_state()
        _cleanup_test_db(db_path, engine)


def test_auth_required_route_rejects_anonymous():
    clear_rate_limit_state()
    db_path, engine, testing_session_local = _build_test_db()

    try:
        with testing_session_local() as db:
            try:
                asyncio.run(get_current_user(credentials=None, db=db))
                raise AssertionError("Anonymous access should be rejected.")
            except HTTPException as exc:
                assert exc.status_code == 401
    finally:
        clear_rate_limit_state()
        _cleanup_test_db(db_path, engine)


def test_rate_limit_blocks_repeated_login_attempts():
    clear_rate_limit_state()
    limiter_dependency = rate_limit("auth_login", limit=5, window_seconds=60)
    request = _request_with_ip("203.0.113.50")

    try:
        for _ in range(5):
            asyncio.run(limiter_dependency(request))

        try:
            asyncio.run(limiter_dependency(request))
            raise AssertionError("Expected rate limit to block the sixth request.")
        except HTTPException as exc:
            assert exc.status_code == 429
    finally:
        clear_rate_limit_state()


def test_authenticated_user_can_be_loaded_from_jwt():
    clear_rate_limit_state()
    db_path, engine, testing_session_local = _build_test_db()

    try:
        with testing_session_local() as db:
            user = create_user(
                db,
                email="pro@example.com",
                password="pro-pass-123",
                role="pro",
            )
            token = create_access_token(user=user)
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token,
            )

            current_user = asyncio.run(get_current_user(credentials=credentials, db=db))
            assert current_user.email == "pro@example.com"
            assert current_user.role == "pro"
    finally:
        clear_rate_limit_state()
        _cleanup_test_db(db_path, engine)


def test_production_settings_reject_insecure_defaults():
    settings = Settings(
        APP_ENV="production",
        DEBUG=False,
        FRONTEND_BASE_URL="https://observerai.example",
        CORS_ALLOWED_ORIGINS="https://observerai.example",
        AUTH_JWT_SECRET=DEFAULT_AUTH_JWT_SECRET,
    )

    try:
        settings.validate_startup()
        raise AssertionError("Production settings should reject the default JWT secret.")
    except RuntimeError as exc:
        assert "AUTH_JWT_SECRET" in str(exc)


def test_operator_bootstrap_preserves_existing_password_hash():
    clear_rate_limit_state()
    db_path, engine, testing_session_local = _build_test_db()

    try:
        with testing_session_local() as db:
            user = create_user(
                db,
                email="operator@example.com",
                password="existing-strong-password",
                role="viewer",
            )
            original_hash = user.password_hash
            settings = Settings(
                OPERATOR_EMAIL="operator@example.com",
                OPERATOR_PASSWORD="new-bootstrap-password",
                OPERATOR_ROLE="admin",
            )

            ensure_operator_user(db, settings)
            refreshed = get_user_by_email(db, "operator@example.com")

            assert refreshed is not None
            assert refreshed.role == "admin"
            assert refreshed.password_hash == original_hash
            assert verify_password("existing-strong-password", refreshed.password_hash)
    finally:
        clear_rate_limit_state()
        _cleanup_test_db(db_path, engine)


def test_admin_login_emits_audit_event():
    clear_rate_limit_state()
    db_path, engine, testing_session_local = _build_test_db()
    handler = _ListHandler()
    audit_logger = logging.getLogger("app.audit")
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)

    try:
        with testing_session_local() as db:
            create_user(
                db,
                email="admin@example.com",
                password="admin-pass-123",
                role="admin",
            )
            request = _request_with_ip("198.51.100.25")
            payload = LoginRequest(email="admin@example.com", password="admin-pass-123")

            response = login(payload=payload, request=request, db=db)

            assert response.role == "admin"
            assert any("action=admin_login" in message for message in handler.messages)
    finally:
        audit_logger.removeHandler(handler)
        clear_rate_limit_state()
        _cleanup_test_db(db_path, engine)
