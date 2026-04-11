"""Shared API dependencies, middleware, and application state."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - optional dependency fallback
    class BackgroundScheduler:  # type: ignore[override]
        def add_job(self, *args, **kwargs) -> None:
            return None

        def start(self) -> None:
            return None

        def shutdown(self, wait: bool = False) -> None:
            return None


try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*args, **kwargs) -> bool:
        return False


from fastapi import Request

from services.analysis.summarizer import GroqSummarizer
from services.api.auth import AuthenticatedPrincipal, AuthManager, is_public_path
from services.api.rate_limit import InMemoryRateLimiter
from services.api.security_headers import security_headers_middleware
from services.api.session_service import SessionService
from services.api.settings import ROOT_DIR, AppSettings
from services.api.telemetry import telemetry_middleware
from services.storage.database import delete_sessions_older_than, init_db

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

load_dotenv(ROOT_DIR / "config" / "env" / ".env")

settings = AppSettings.from_env()
logger = logging.getLogger("snapback.api")
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

scheduler = BackgroundScheduler()
auth_manager = AuthManager(settings)
rate_limiter = InMemoryRateLimiter(
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
session_service = SessionService(
    root_dir=ROOT_DIR,
    settings=settings,
    summarizer=GroqSummarizer(api_key=settings.groq_api_key),
)


def get_request_principal(request: Request) -> AuthenticatedPrincipal:
    """Return the authenticated principal attached by middleware."""
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise RuntimeError("Authenticated principal was not set on the request.")
    return principal


@asynccontextmanager
async def lifespan(_app) -> AsyncGenerator[None, None]:
    """Handle application lifespan events."""
    init_db()
    scheduler.add_job(
        delete_sessions_older_than,
        "interval",
        hours=settings.auto_delete_after_hours,
        args=[settings.auto_delete_after_hours],
        id="cleanup-old-sessions",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("SnapBack API started")
    yield
    scheduler.shutdown(wait=False)
    logger.info("SnapBack API stopped")


async def attach_security_context(request: Request, call_next):
    """Attach auth, telemetry, rate limiting, and security headers."""

    async def secured_call(next_request: Request):
        if not is_public_path(next_request.url.path):
            principal = auth_manager.authenticate(next_request)
            next_request.state.principal = principal
            client_host = next_request.client.host if next_request.client else "unknown"
            rate_limiter.enforce(
                f"{principal.principal_id}:{client_host}:{next_request.url.path}"
            )
        return await telemetry_middleware(next_request, call_next)

    return await security_headers_middleware(request, secured_call)
