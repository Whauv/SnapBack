from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - optional dependency fallback
    class BackgroundScheduler:  # type: ignore[override]
        def add_job(self, *args: Any, **kwargs: Any) -> None:
            return None

        def start(self) -> None:
            return None

        def shutdown(self, wait: bool = False) -> None:
            return None
try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field, field_validator

from services.analysis.detector import detect_missed_alerts, detect_topic_shift
from services.analysis.summarizer import GroqSummarizer
from services.exporters.export import build_markdown_export, build_pdf_export, export_to_notion
from services.storage.database import (
    append_transcript_chunk,
    create_session,
    delete_sessions_older_than,
    end_session,
    get_first_chunk_after,
    get_last_chunk_before,
    get_recaps,
    get_session,
    get_session_bundle,
    get_transcript,
    get_transcript_window,
    init_db,
    save_audio_chunk,
    save_recap,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "config" / "env" / ".env")

logger = logging.getLogger("snapback.api")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

TIMESTAMP_ERROR = "Timestamps must be valid ISO-8601 strings."
MAX_TRANSCRIPT_CHARS = int(os.getenv("MAX_TRANSCRIPT_CHARS", "8000"))
MAX_AUDIO_CHUNK_BYTES = int(os.getenv("MAX_AUDIO_CHUNK_BYTES", str(5 * 1024 * 1024)))
SUPPORTED_AUDIO_MIME_TYPES = {"audio/webm", "audio/wav", "audio/mp4", "application/octet-stream"}


def _parse_timestamp(value: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(TIMESTAMP_ERROR) from error
    return value


def _clean_text(value: str, *, field_name: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _parse_allowed_origins(raw_value: str) -> list[str]:
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]


@dataclass(frozen=True)
class AppSettings:
    auto_delete_after_hours: int
    notion_api_key: str
    groq_api_key: str | None
    cors_origins: list[str]

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            auto_delete_after_hours=max(1, int(os.getenv("AUTO_DELETE_AFTER_HOURS", "24"))),
            notion_api_key=os.getenv("NOTION_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            cors_origins=_parse_allowed_origins(os.getenv("CORS_ALLOW_ORIGINS", "")),
        )


settings = AppSettings.from_env()
scheduler = BackgroundScheduler()
summarizer = GroqSummarizer(api_key=settings.groq_api_key)


class SessionStartRequest(BaseModel):
    mode: Literal["cloud", "local"] = "cloud"
    language: str = Field(default="English", min_length=2, max_length=32)
    recap_length: Literal["brief", "standard", "detailed"] = "standard"

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _clean_text(value, field_name="language")


class TranscriptChunkRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=MAX_TRANSCRIPT_CHARS)
    timestamp: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return _clean_text(value, field_name="session_id")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _clean_text(value, field_name="text")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return _parse_timestamp(value)


class RecapRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    from_timestamp: str
    to_timestamp: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return _clean_text(value, field_name="session_id")

    @field_validator("from_timestamp", "to_timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return _parse_timestamp(value)


class SessionEndRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return _clean_text(value, field_name="session_id")


class ExportRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return _clean_text(value, field_name="session_id")


class AudioChunkRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    chunk_index: int = Field(ge=0, le=1_000_000)
    mime_type: str = Field(min_length=1, max_length=64)
    audio_base64: str = Field(min_length=1)
    timestamp: str
    source: str = Field(default="extension", min_length=1, max_length=32)

    @field_validator("session_id", "source")
    @classmethod
    def validate_identifiers(cls, value: str, info: Any) -> str:
        return _clean_text(value, field_name=info.field_name)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        mime_type = _clean_text(value, field_name="mime_type").lower()
        if mime_type not in SUPPORTED_AUDIO_MIME_TYPES:
            raise ValueError("Unsupported audio mime_type.")
        return mime_type

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return _parse_timestamp(value)


class NotionExportRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    page_id: str = Field(min_length=1, max_length=128)
    notion_api_key: str | None = Field(default=None, max_length=256)

    @field_validator("session_id", "page_id")
    @classmethod
    def validate_values(cls, value: str, info: Any) -> str:
        return _clean_text(value, field_name=info.field_name)


class StudyPackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return _clean_text(value, field_name="session_id")


def _ensure_session_exists(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _build_bundle_or_404(session_id: str):
    bundle = get_session_bundle(session_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Session not found")
    return bundle


def _extension_for_mime_type(mime_type: str) -> str:
    return {
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/mp4": "mp4",
        "application/octet-stream": "bin",
    }.get(mime_type, "bin")


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(title="SnapBack API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session/start")
def start_session(payload: SessionStartRequest) -> dict[str, Any]:
    session = create_session(payload.mode, payload.language, payload.recap_length)
    logger.info("Started session %s in %s mode", session["id"], payload.mode)
    return {"session_id": session["id"], "start_timestamp": session["start_timestamp"], "session": session}


@app.post("/session/transcript")
def ingest_transcript(payload: TranscriptChunkRequest) -> dict[str, Any]:
    _ensure_session_exists(payload.session_id)
    chunk = append_transcript_chunk(payload.session_id, payload.text, payload.timestamp)
    return {"chunk": chunk}


@app.post("/session/audio-chunk")
def ingest_audio_chunk(payload: AudioChunkRequest) -> dict[str, Any]:
    _ensure_session_exists(payload.session_id)

    try:
        audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Invalid audio payload: {error}") from error

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio payload cannot be empty.")
    if len(audio_bytes) > MAX_AUDIO_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="Audio payload exceeds the configured size limit.")

    audio_dir = ROOT_DIR / "data" / "audio" / payload.session_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    extension = _extension_for_mime_type(payload.mime_type)
    file_path = audio_dir / f"chunk-{payload.chunk_index:06d}.{extension}"
    file_path.write_bytes(audio_bytes)

    chunk = save_audio_chunk(
        payload.session_id,
        chunk_index=payload.chunk_index,
        mime_type=payload.mime_type,
        file_path=str(file_path),
        timestamp=payload.timestamp,
        source=payload.source,
    )
    return {"audio_chunk": chunk}


@app.post("/recap")
def generate_recap(payload: RecapRequest) -> dict[str, Any]:
    session = _ensure_session_exists(payload.session_id)
    if payload.from_timestamp > payload.to_timestamp:
        raise HTTPException(status_code=400, detail="from_timestamp must be earlier than to_timestamp.")

    chunks = get_transcript_window(payload.session_id, payload.from_timestamp, payload.to_timestamp)
    transcript_text = "\n".join(chunk["text"] for chunk in chunks)
    summary = summarizer.generate_summary(
        transcript_text,
        language=session.get("language", "English"),
        recap_length=session.get("recap_length", "standard"),
    )
    keywords = summarizer.extract_keywords(transcript_text)
    previous_chunk = get_last_chunk_before(payload.session_id, payload.from_timestamp)
    current_chunk = get_first_chunk_after(payload.session_id, payload.to_timestamp)
    comparison_chunk = current_chunk or (chunks[-1] if chunks else None) or (chunks[0] if chunks else None)
    topic_shift_detected = detect_topic_shift(
        previous_chunk["text"] if previous_chunk else None,
        comparison_chunk["text"] if comparison_chunk else None,
    )
    missed_alerts = detect_missed_alerts(chunks)
    recap = save_recap(
        payload.session_id,
        payload.from_timestamp,
        payload.to_timestamp,
        summary,
        keywords,
        topic_shift_detected,
        missed_alerts,
    )
    return {
        "summary": summary,
        "keywords": keywords,
        "topic_shift_detected": topic_shift_detected,
        "missed_alerts": missed_alerts,
        "topic_shift_reference": {
            "before_departure": previous_chunk["timestamp"] if previous_chunk else None,
            "comparison_chunk": comparison_chunk["timestamp"] if comparison_chunk else None,
        },
        "recap": recap,
    }


@app.get("/session/{session_id}/transcript")
def get_session_transcript(session_id: str) -> dict[str, Any]:
    session = _ensure_session_exists(session_id)
    return {
        "session": session,
        "transcript": get_transcript(session_id),
        "recaps": get_recaps(session_id),
    }


@app.post("/session/end")
def complete_session(payload: SessionEndRequest) -> dict[str, Any]:
    session = _ensure_session_exists(payload.session_id)
    transcript = get_transcript(payload.session_id)
    transcript_text = "\n".join(chunk["text"] for chunk in transcript)
    full_summary = summarizer.summarize_full_session(transcript_text, language=session.get("language", "English"))
    updated_session = end_session(payload.session_id, full_summary)
    logger.info("Ended session %s", payload.session_id)
    return {"full_summary": full_summary, "session": updated_session}


@app.post("/export/pdf")
def export_pdf(payload: ExportRequest) -> Response:
    bundle = _build_bundle_or_404(payload.session_id)
    pdf_bytes = build_pdf_export({"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps})
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/export/markdown")
def export_markdown(payload: ExportRequest) -> Response:
    bundle = _build_bundle_or_404(payload.session_id)
    markdown = build_markdown_export(
        {"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps}
    )
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.md"'}
    return Response(content=markdown, media_type="text/markdown; charset=utf-8", headers=headers)


@app.post("/export/notion")
def export_notion(payload: NotionExportRequest) -> dict[str, Any]:
    bundle = _build_bundle_or_404(payload.session_id)
    api_key = payload.notion_api_key or settings.notion_api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing Notion API key")
    return export_to_notion(
        {"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps},
        api_key=api_key,
        page_id=payload.page_id,
    )


@app.post("/study/pack")
def generate_study_pack(payload: StudyPackRequest) -> dict[str, Any]:
    bundle = _build_bundle_or_404(payload.session_id)
    transcript_text = "\n".join(chunk["text"] for chunk in bundle.transcript)
    study_pack = summarizer.generate_study_pack(
        transcript_text,
        language=bundle.session.get("language", "English"),
    )
    return {
        "session_id": payload.session_id,
        "study_pack": study_pack,
    }
