import logging

from sqlalchemy import inspect, select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import candle, market_state, signal, signal_outcome, user  # noqa: F401
from app.core.config import get_settings
from app.models.user import User
from app.services.auth_service import ensure_operator_user

logger = logging.getLogger(__name__)


SIGNAL_COLUMN_DEFINITIONS = {
    "current_price": "FLOAT",
    "bias": "VARCHAR(50)",
    "resolved_bias": "VARCHAR(50)",
    "anchor_direction": "VARCHAR(20)",
    "anchor_type": "VARCHAR(20)",
    "adr": "FLOAT",
    "adr_used_pct": "FLOAT",
    "adr_state": "VARCHAR(20)",
    "nearest_magnet": "TEXT",
    "major_magnet": "TEXT",
    "magnet_path": "TEXT",
    "sweep": "TEXT",
    "structure": "TEXT",
    "momentum": "TEXT",
    "mid_targets": "TEXT",
    "intent": "TEXT",
}

USER_COLUMN_DEFINITIONS = {
    "password_hash": "VARCHAR(255)",
    "role": "VARCHAR(20) DEFAULT 'viewer'",
    "is_active": "BOOLEAN DEFAULT TRUE",
}


def _ensure_columns(table_name: str, column_definitions: dict[str, str]) -> None:
    """Add newer columns to an existing table using dialect-safe inspection."""
    with engine.begin() as conn:
        inspector = inspect(conn)
        if table_name not in inspector.get_table_names():
            return

        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        preparer = conn.dialect.identifier_preparer
        quoted_table = preparer.quote(table_name)

        for column_name, column_type in column_definitions.items():
            if column_name not in existing_columns:
                quoted_column = preparer.quote(column_name)
                conn.exec_driver_sql(
                    f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {column_type}"
                )


def _ensure_signal_columns() -> None:
    """Add newer signal columns to an existing table when needed."""

    _ensure_columns("signals", SIGNAL_COLUMN_DEFINITIONS)


def _ensure_user_columns() -> None:
    """Add newer user columns to an existing table when needed."""

    _ensure_columns("users", USER_COLUMN_DEFINITIONS)


def _is_auto_generated_id(column: dict[str, object], dialect_name: str) -> bool:
    """Return whether an inspected id column appears database-generated."""

    if dialect_name == "sqlite":
        return bool(column.get("primary_key")) and (
            "integer" in str(column.get("type")).lower()
        )

    if dialect_name == "postgresql":
        default = str(column.get("default") or "").lower()
        return bool(column.get("identity")) or "nextval(" in default

    return column.get("autoincrement") is True or bool(column.get("identity"))


def _warn_if_user_id_not_autoincrement() -> None:
    """Warn when an existing users table cannot auto-generate primary keys."""

    with engine.begin() as conn:
        inspector = inspect(conn)
        if "users" not in inspector.get_table_names():
            return

        id_column = next(
            (
                column
                for column in inspector.get_columns("users")
                if column["name"] == "id"
            ),
            None,
        )
        if id_column is None or _is_auto_generated_id(id_column, conn.dialect.name):
            return

        logger.warning(
            "Existing users.id column does not appear to be auto-generated for dialect=%s. "
            "Base.metadata.create_all() cannot repair existing columns; run a migration or reset the database.",
            conn.dialect.name,
        )


def _seed_operator_user() -> None:
    settings = get_settings()

    db = SessionLocal()
    try:
        has_active_admin = db.scalar(
            select(User.id)
            .where(User.role == "admin", User.is_active.is_(True))
            .limit(1)
        )
        if settings.is_production and not settings.operator_bootstrap_configured and not has_active_admin:
            raise RuntimeError(
                "Production launch requires an active admin user or OPERATOR_EMAIL/OPERATOR_PASSWORD bootstrap credentials."
            )
        if not settings.operator_bootstrap_configured:
            return
        ensure_operator_user(db, settings)
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_signal_columns()
    _ensure_user_columns()
    _warn_if_user_id_not_autoincrement()
    _seed_operator_user()
