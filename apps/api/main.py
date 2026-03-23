from __future__ import annotations

import os
import base64
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

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
from services.analysis.detector import detect_missed_alerts, detect_topic_shift
from services.analysis.summarizer import GroqSummarizer
from services.exporters.export import build_markdown_export, build_pdf_export, export_to_notion

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "config" / "env" / ".env")

AUTO_DELETE_AFTER_HOURS = int(os.getenv("AUTO_DELETE_AFTER_HOURS", "24"))
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")


class SessionStartRequest(BaseModel):
    mode: Literal["cloud", "local"] = "cloud"
    language: str = "English"
    recap_length: Literal["brief", "standard", "detailed"] = "standard"


class TranscriptChunkRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1)
    timestamp: str


class RecapRequest(BaseModel):
    session_id: str
    from_timestamp: str
    to_timestamp: str


class SessionEndRequest(BaseModel):
    session_id: str


class ExportRequest(BaseModel):
    session_id: str


class AudioChunkRequest(BaseModel):
    session_id: str
    chunk_index: int
    mime_type: str
    audio_base64: str
    timestamp: str
    source: str = "extension"


class NotionExportRequest(BaseModel):
    session_id: str
    page_id: str
    notion_api_key: str | None = None


scheduler = BackgroundScheduler()
summarizer = GroqSummarizer(api_key=os.getenv("GROQ_API_KEY"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(
        delete_sessions_older_than,
        "interval",
        hours=max(AUTO_DELETE_AFTER_HOURS, 1),
        args=[AUTO_DELETE_AFTER_HOURS],
        id="cleanup-old-sessions",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="SnapBack API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session/start")
def start_session(payload: SessionStartRequest) -> dict:
    session = create_session(payload.mode, payload.language, payload.recap_length)
    return {"session_id": session["id"], "start_timestamp": session["start_timestamp"], "session": session}


@app.post("/session/transcript")
def ingest_transcript(payload: TranscriptChunkRequest) -> dict:
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    chunk = append_transcript_chunk(payload.session_id, payload.text, payload.timestamp)
    return {"chunk": chunk}


@app.post("/session/audio-chunk")
def ingest_audio_chunk(payload: AudioChunkRequest) -> dict:
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        audio_bytes = base64.b64decode(payload.audio_base64)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Invalid audio payload: {error}") from error

    audio_dir = ROOT_DIR / "data" / "audio" / payload.session_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    extension = "webm" if "webm" in payload.mime_type else "bin"
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
def generate_recap(payload: RecapRequest) -> dict:
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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
def get_session_transcript(session_id: str) -> dict:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": session,
        "transcript": get_transcript(session_id),
        "recaps": get_recaps(session_id),
    }


@app.post("/session/end")
def complete_session(payload: SessionEndRequest) -> dict:
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    transcript = get_transcript(payload.session_id)
    transcript_text = "\n".join(chunk["text"] for chunk in transcript)
    full_summary = summarizer.summarize_full_session(transcript_text, language=session.get("language", "English"))
    updated_session = end_session(payload.session_id, full_summary)
    return {"full_summary": full_summary, "session": updated_session}


@app.post("/export/pdf")
def export_pdf(payload: ExportRequest) -> Response:
    bundle = get_session_bundle(payload.session_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Session not found")
    pdf_bytes = build_pdf_export(
        {"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps}
    )
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/export/markdown")
def export_markdown(payload: ExportRequest) -> Response:
    bundle = get_session_bundle(payload.session_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Session not found")
    markdown = build_markdown_export(
        {"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps}
    )
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.md"'}
    return Response(content=markdown, media_type="text/markdown", headers=headers)


@app.post("/export/notion")
def export_notion(payload: NotionExportRequest) -> dict:
    bundle = get_session_bundle(payload.session_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Session not found")
    api_key = payload.notion_api_key or NOTION_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing Notion API key")
    return export_to_notion(
        {"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps},
        api_key=api_key,
        page_id=payload.page_id,
    )
