import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.responses import Response

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.landing import build_landing_page_html
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.api.dashboard import router as dashboard_router
from app.api.ingest import router as ingest_router
from app.api.oracle import router as oracle_router
from app.api.performance import router as performance_router
from app.api.signals import router as signals_router
from app.api.market_map import router as market_map_router

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
settings.validate_startup()
app = FastAPI(title=settings.app_name, debug=settings.debug)

if settings.is_production and "*" in settings.cors_allowed_origins:
    raise RuntimeError("Wildcard CORS origins are not allowed in production.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.on_event('startup')
def on_startup() -> None:
    init_db()
    if not settings.stripe_secret_key:
        logger.warning("Stripe checkout is disabled until STRIPE_SECRET_KEY is configured.")
    if not settings.operator_bootstrap_configured:
        logger.info("Operator bootstrap is disabled; no OPERATOR_EMAIL/OPERATOR_PASSWORD configured.")


@app.middleware("http")
async def harden_http_responses(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "form-action 'self' https://checkout.stripe.com; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "font-src 'self' data:;",
    )
    if request.url.path.startswith(("/auth", "/admin", "/billing")):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.get('/', response_class=HTMLResponse)
def root() -> HTMLResponse:
    return HTMLResponse(build_landing_page_html())


@app.get('/health')
def health():
    return {'message': f'{settings.app_name} running', 'env': settings.app_env}


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(ingest_router)
app.include_router(oracle_router)
app.include_router(signals_router)
app.include_router(performance_router)
app.include_router(market_map_router)
app.include_router(dashboard_router)
