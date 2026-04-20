from sqlalchemy import select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import candle, market_state, signal, signal_outcome, user  # noqa: F401
from app.core.config import get_settings
from app.models.user import User
from app.services.auth_service import ensure_operator_user


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
    "is_active": "BOOLEAN DEFAULT 1",
}


def _ensure_signal_columns() -> None:
    """Add newer signal columns to an existing SQLite table when needed."""

    with engine.begin() as conn:
        existing_tables = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "signals" not in existing_tables:
            return

        existing_columns = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(signals)")
        }

        for column_name, column_type in SIGNAL_COLUMN_DEFINITIONS.items():
            if column_name not in existing_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE signals ADD COLUMN {column_name} {column_type}"
                )


def _ensure_user_columns() -> None:
    """Add newer user columns to an existing SQLite table when needed."""

    with engine.begin() as conn:
        existing_tables = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "users" not in existing_tables:
            return

        existing_columns = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")
        }

        for column_name, column_type in USER_COLUMN_DEFINITIONS.items():
            if column_name not in existing_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
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
    _seed_operator_user()
