"""Session lifecycle and transcript routes."""

from fastapi import Request

from apps.api.dependencies import get_request_principal, logger, session_service, settings
from apps.api.routes._compat import APIRouter
from services.api.contracts import (
    AudioChunkRequest,
    SessionEndRequest,
    SessionStartRequest,
    TranscriptChunkRequest,
)

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/start")
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


@router.post("/transcript")
def ingest_transcript(payload: TranscriptChunkRequest, request: Request) -> dict:
    """Ingest a transcript chunk into the database."""
    principal = get_request_principal(request)
    return session_service.ingest_transcript(
        principal=principal,
        session_id=payload.session_id,
        text=payload.text[: settings.max_transcript_chars],
        timestamp=payload.timestamp,
    )


@router.post("/audio-chunk")
def ingest_audio_chunk(payload: AudioChunkRequest, request: Request) -> dict:
    """Ingest an audio chunk and save it to disk."""
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


@router.get("/{session_id}/transcript")
def get_session_transcript(session_id: str, request: Request) -> dict:
    """Get the full transcript and metadata for a session."""
    principal = get_request_principal(request)
    return session_service.get_session_transcript(principal=principal, session_id=session_id)


@router.post("/end")
def complete_session(payload: SessionEndRequest, request: Request) -> dict:
    """Complete a session and generate a full summary."""
    principal = get_request_principal(request)
    result = session_service.complete_session(principal=principal, session_id=payload.session_id)
    logger.info("Ended session %s for %s", payload.session_id, principal.principal_id)
    return result
