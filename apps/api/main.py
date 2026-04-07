"""API endpoints for SnapBack."""

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


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse, Response

from services.analysis.summarizer import GroqSummarizer
from services.api.auth import AuthManager, AuthenticatedPrincipal, is_public_path
from services.api.contracts import (
    AudioChunkRequest,
    ExportRequest,
    NotionExportRequest,
    RecapRequest,
    SessionEndRequest,
    SessionStartRequest,
    StudyPackRequest,
    TranscriptChunkRequest,
)
from services.api.rate_limit import InMemoryRateLimiter
from services.api.security_headers import security_headers_middleware
from services.api.session_service import SessionService
from services.api.settings import AppSettings, ROOT_DIR
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
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise RuntimeError("Authenticated principal was not set on the request.")
    return principal


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
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


@app.middleware("http")
async def attach_security_context(request: Request, call_next):
    async def secured_call(next_request: Request):
        if not is_public_path(next_request.url.path):
            principal = auth_manager.authenticate(next_request)
            next_request.state.principal = principal
            client_host = next_request.client.host if next_request.client else "unknown"
            rate_limiter.enforce(f"{principal.principal_id}:{client_host}:{next_request.url.path}")
        return await telemetry_middleware(next_request, call_next)

    return await security_headers_middleware(request, secured_call)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs" if settings.allow_docs else "/health")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Check the health of the API."""
    return {"status": "ok"}


@app.post("/session/start")
def start_session(payload: SessionStartRequest, request: Request) -> dict:
    """Start a new session."""
    principal = get_request_principal(request)
    result = session_service.start_session(
        principal=principal,
        mode=payload.mode,
        language=payload.language,
        recap_length=payload.recap_length,
    )
    logger.info("Started session %s for %s", result["session_id"], principal.principal_id)
    return result


@app.post("/session/transcript")
def ingest_transcript(payload: TranscriptChunkRequest, request: Request) -> dict:
    """Ingest a transcript chunk into the database."""
    principal = get_request_principal(request)
    return session_service.ingest_transcript(
        principal=principal,
        session_id=payload.session_id,
        text=payload.text[: settings.max_transcript_chars],
        timestamp=payload.timestamp,
    )


@app.post("/session/audio-chunk")
def ingest_audio_chunk(payload: AudioChunkRequest, request: Request) -> dict:
    """Ingest an audio chunk and save it to the disk."""
    principal = get_request_principal(request)
    return session_service.ingest_audio_chunk(
        principal=principal,
        session_id=payload.session_id,
        chunk_index=payload.chunk_index,
        mime_type=payload.mime_type,
        audio_base64=payload.audio_base64,
        timestamp=payload.timestamp,
        source=payload.source,
    )


@app.post("/recap")
def generate_recap(payload: RecapRequest, request: Request) -> dict:
    """Generate a recap for a specific time window within a session."""
    principal = get_request_principal(request)
    return session_service.generate_recap(
        principal=principal,
        session_id=payload.session_id,
        from_timestamp=payload.from_timestamp,
        to_timestamp=payload.to_timestamp,
    )


@app.get("/session/{session_id}/transcript")
def get_session_transcript(session_id: str, request: Request) -> dict:
    """Get the full transcript and metadata for a session."""
    principal = get_request_principal(request)
    return session_service.get_session_transcript(principal=principal, session_id=session_id)


@app.post("/session/end")
def complete_session(payload: SessionEndRequest, request: Request) -> dict:
    """Complete a session and generate a full summary."""
    principal = get_request_principal(request)
    result = session_service.complete_session(principal=principal, session_id=payload.session_id)
    logger.info("Ended session %s for %s", payload.session_id, principal.principal_id)
    return result


@app.post("/export/pdf")
def export_pdf(payload: ExportRequest, request: Request) -> Response:
    """Export the session as a PDF document."""
    principal = get_request_principal(request)
    pdf_bytes = session_service.export_pdf(principal=principal, session_id=payload.session_id)
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/export/markdown")
def export_markdown(payload: ExportRequest, request: Request) -> Response:
    """Export the session as a Markdown document."""
    principal = get_request_principal(request)
    markdown = session_service.export_markdown(principal=principal, session_id=payload.session_id)
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.md"'}
    return Response(content=markdown, media_type="text/markdown; charset=utf-8", headers=headers)


@app.post("/export/notion")
def export_notion(payload: NotionExportRequest, request: Request) -> dict:
    """Export the session to a Notion page."""
    principal = get_request_principal(request)
    return session_service.export_notion(
        principal=principal,
        session_id=payload.session_id,
        page_id=payload.page_id,
        notion_api_key=payload.notion_api_key,
    )


@app.post("/study/pack")
def generate_study_pack(payload: StudyPackRequest, request: Request) -> dict:
    """Generate a study pack for a session."""
    principal = get_request_principal(request)
    return session_service.generate_study_pack(principal=principal, session_id=payload.session_id)
