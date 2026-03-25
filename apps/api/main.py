"""SnapBack API."""

# ruff: noqa: SLF001

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import fastapi
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

import services.facade.api_gateway as gw
from apps.api.schemas import (
    AudioChunkRequest,
    RecapRequest,
    SessionRequest,
    SnapBackResponse,
)
from services.jobs import bootstrap_system

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


router = fastapi.APIRouter()


def _attachment_headers(session_id: str, extension: str) -> dict[str, str]:
    content_disposition = f'attachment; filename="snapback-{session_id}.{extension}"'
    return {"Content-Disposition": content_disposition}


@asynccontextmanager
async def _lifespan(_app: fastapi.FastAPI) -> AsyncIterator[None]:
    sys_manager = bootstrap_system()
    yield
    sys_manager.shutdown(wait=False)


def _build_http_app() -> fastapi.FastAPI:
    return fastapi.FastAPI(title="SnapBack API", version="0.1.0", lifespan=_lifespan)


def _configure_cors(app: fastapi.FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_routes(app: fastapi.FastAPI) -> None:
    app.include_router(router)


@router.get("/health", response_model=SnapBackResponse)
def health_check() -> SnapBackResponse:
    """Health check endpoint returning service status."""
    return SnapBackResponse.health()


@router.post("/session/start", response_model=SnapBackResponse)
def start_session(payload: SessionRequest) -> SnapBackResponse:
    """Start a new session with provided parameters."""
    return SnapBackResponse._from_start(dict(gw.start_op(*payload.start_args())))


@router.post("/session/transcript", response_model=SnapBackResponse)
def ingest_transcript(payload: SessionRequest) -> SnapBackResponse:
    """Ingest a transcript segment for a session."""
    return SnapBackResponse._from_transcript(
        dict(gw.ingest_op(*payload.transcript_args())),
    )


@router.post("/session/audio-chunk", response_model=SnapBackResponse)
def ingest_audio_chunk(payload: AudioChunkRequest) -> SnapBackResponse:
    """Receive and persist an audio chunk for a session."""
    try:
        (
            session_id,
            chunk_index,
            mime_type,
            raw,
            timestamp,
            source,
        ) = payload.audio_args()
    except ValueError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc
    return SnapBackResponse._from_audio(
        dict(
            gw.save_op(
                session_id,
                chunk_index,
                mime_type,
                raw,
                timestamp,
                source,
            ),
        ),
    )


@router.post("/recap", response_model=SnapBackResponse)
def generate_recap(payload: RecapRequest) -> SnapBackResponse:
    """Generate a recap for a session using configured parameters."""
    return SnapBackResponse._from_recap(dict(gw.recap_op(*payload.recap_args())))


@router.get("/session/{session_id}/transcript", response_model=SnapBackResponse)
def get_session_transcript(session_id: str) -> SnapBackResponse:
    """Fetch the transcript bundle for the given session id."""
    return SnapBackResponse._from_bundle(dict(gw.bundle_op(session_id)))


@router.post("/session/end", response_model=SnapBackResponse)
def complete_session(payload: SessionRequest) -> SnapBackResponse:
    """Mark a session as complete and run finalization tasks."""
    return SnapBackResponse._from_end(dict(gw.end_op(payload.session())))


@router.post("/export/pdf")
def export_pdf(payload: SessionRequest) -> Response:
    """Export session content as a PDF attachment."""
    session_id = payload.session()
    return Response(
        content=gw.pdf_op(session_id),
        media_type="application/pdf",
        headers=_attachment_headers(session_id, "pdf"),
    )


@router.post("/export/markdown")
def export_markdown(payload: SessionRequest) -> Response:
    """Export session content as Markdown attachment."""
    session_id = payload.session()
    return Response(
        content=gw.md_op(session_id),
        media_type="text/markdown",
        headers=_attachment_headers(session_id, "md"),
    )


@router.post("/export/notion", response_model=SnapBackResponse)
def export_notion(payload: SessionRequest) -> SnapBackResponse:
    """Send session content to Notion using configured credentials."""
    return SnapBackResponse._from_notion(dict(gw.notion_op(*payload.notion_args())))


@router.post("/study/pack", response_model=SnapBackResponse)
def generate_study_pack(payload: SessionRequest) -> SnapBackResponse:
    """Generate a study pack for the given session id."""
    return SnapBackResponse._from_study_pack(dict(gw.study_op(payload.session())))


def create_app() -> fastapi.FastAPI:
    """Create and configure the FastAPI application."""
    app = _build_http_app()
    _configure_cors(app)
    _register_routes(app)
    return app


app = create_app()
