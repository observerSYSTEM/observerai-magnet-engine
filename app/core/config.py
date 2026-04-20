from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AUTH_JWT_SECRET = 'change-me-observerai-jwt-secret'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = Field(default='ObserverAI Magnet Engine', alias='APP_NAME')
    app_env: str = Field(default='dev', alias='APP_ENV')
    debug: bool = Field(default=True, alias='DEBUG')
    database_url: str = Field(default='sqlite:///./observerai.db', alias='DATABASE_URL')
    telegram_bot_token: str = Field(default='', alias='TELEGRAM_BOT_TOKEN')
    telegram_chat_id: str = Field(default='', alias='TELEGRAM_CHAT_ID')
    telegram_alerts_enabled: bool = Field(default=False, alias='TELEGRAM_ALERTS_ENABLED')
    mt5_login: int | None = Field(default=None, alias='MT5_LOGIN')
    mt5_password: str = Field(default='', alias='MT5_PASSWORD')
    mt5_server: str = Field(default='', alias='MT5_SERVER')
    mt5_terminal_path: str = Field(default='', alias='MT5_TERMINAL_PATH')
    api_base_url: str = Field(default='http://127.0.0.1:8000', alias='API_BASE_URL')
    stripe_secret_key: str = Field(default='', alias='STRIPE_SECRET_KEY')
    frontend_base_url: str = Field(default='http://127.0.0.1:8000', alias='FRONTEND_BASE_URL')
    cors_allowed_origins_raw: str = Field(default='', alias='CORS_ALLOWED_ORIGINS')
    auth_jwt_secret: str = Field(default=DEFAULT_AUTH_JWT_SECRET, alias='AUTH_JWT_SECRET')
    auth_access_token_expire_minutes: int = Field(default=60, alias='AUTH_ACCESS_TOKEN_EXPIRE_MINUTES')
    operator_email: str = Field(default='', alias='OPERATOR_EMAIL')
    operator_password: str = Field(default='', alias='OPERATOR_PASSWORD')
    operator_role: Literal['viewer', 'pro', 'elite', 'admin'] = Field(default='admin', alias='OPERATOR_ROLE')
    runner_interval_seconds: int = Field(default=60, alias='RUNNER_INTERVAL_SECONDS')
    default_symbol: str = Field(default='XAUUSD', alias='DEFAULT_SYMBOL')
    london_utc_offset: int = Field(default=0, alias='LONDON_UTC_OFFSET')
    adr_lookback_days: int = Field(default=5, alias='ADR_LOOKBACK_DAYS')

    @property
    def cors_allowed_origins(self) -> list[str]:
        raw = self.cors_allowed_origins_raw.strip()
        if raw:
            return [origin.strip() for origin in raw.split(',') if origin.strip()]
        if self.frontend_base_url:
            return [self.frontend_base_url.rstrip('/')]
        return []

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {'prod', 'production'}

    @property
    def auth_jwt_secret_is_default(self) -> bool:
        return self.auth_jwt_secret == DEFAULT_AUTH_JWT_SECRET

    @property
    def operator_bootstrap_configured(self) -> bool:
        return bool(self.operator_email and self.operator_password)

    @staticmethod
    def _validate_origin(origin: str, *, production: bool) -> None:
        parsed = urlparse(origin)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise RuntimeError(f'Invalid origin configured: {origin}')
        if parsed.path not in {'', '/'} or parsed.params or parsed.query or parsed.fragment:
            raise RuntimeError(f'Origin must not include path/query/fragment: {origin}')
        if production and parsed.scheme != 'https':
            raise RuntimeError(f'Production origins must use https: {origin}')

    def validate_startup(self) -> None:
        if self.auth_access_token_expire_minutes <= 0:
            raise RuntimeError('AUTH_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0.')
        if self.runner_interval_seconds <= 0:
            raise RuntimeError('RUNNER_INTERVAL_SECONDS must be greater than 0.')

        has_operator_email = bool(self.operator_email)
        has_operator_password = bool(self.operator_password)
        if has_operator_email != has_operator_password:
            raise RuntimeError(
                'OPERATOR_EMAIL and OPERATOR_PASSWORD must either both be set or both be empty.'
            )

        if not self.is_production:
            return

        if self.debug:
            raise RuntimeError('DEBUG must be false in production.')
        if not self.cors_allowed_origins:
            raise RuntimeError('CORS_ALLOWED_ORIGINS must be set in production.')

        self._validate_origin(self.frontend_base_url.rstrip('/'), production=True)
        for origin in self.cors_allowed_origins:
            self._validate_origin(origin, production=True)
        if self.frontend_base_url.rstrip('/') not in self.cors_allowed_origins:
            raise RuntimeError(
                'FRONTEND_BASE_URL must also be included in CORS_ALLOWED_ORIGINS in production.'
            )

        if self.auth_jwt_secret_is_default or len(self.auth_jwt_secret) < 32:
            raise RuntimeError(
                'AUTH_JWT_SECRET must be set to a strong non-default value in production.'
            )

        if self.telegram_alerts_enabled and (
            not self.telegram_bot_token or not self.telegram_chat_id
        ):
            raise RuntimeError(
                'TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required when TELEGRAM_ALERTS_ENABLED=true.'
            )

        if has_operator_email:
            if self.operator_role != 'admin':
                raise RuntimeError('OPERATOR_ROLE must be admin for production bootstrap.')
            if self.operator_password.startswith('change-me') or len(self.operator_password) < 12:
                raise RuntimeError(
                    'OPERATOR_PASSWORD must be a strong non-placeholder secret in production.'
                )


@lru_cache
def get_settings() -> Settings:
    return Settings()
