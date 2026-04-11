"""App factory for the SnapBack API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from apps.api.dependencies import attach_security_context, lifespan, settings
from apps.api.routes.export import router as export_router
from apps.api.routes.health import router as health_router
from apps.api.routes.recap import router as recap_router
from apps.api.routes.session import router as session_router
from apps.api.routes.study import router as study_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SnapBack API",
        version="0.3.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.allow_docs else None,
        redoc_url="/redoc" if settings.allow_docs else None,
        openapi_url="/openapi.json" if settings.allow_docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "X-SnapBack-Token"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.middleware("http")(attach_security_context)

    if hasattr(app, "include_router"):
        app.include_router(health_router)
        app.include_router(session_router)
        app.include_router(recap_router)
        app.include_router(export_router)
        app.include_router(study_router)
    return app
