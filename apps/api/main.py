"""SnapBack API. Restored user endpoints."""

from __future__ import annotations
import base64
import binascii
from typing import Literal, Any

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from services.facade.api_gateway import (
    start_op, ingest_op, save_op, recap_op, bundle_op, end_op,
    pdf_op, md_op, notion_op, study_op
)

class SessionStartRequest(BaseModel):
    """Request to start a new session."""
    model_config = ConfigDict(extra="forbid")
    mode: Literal["cloud", "local"] = "cloud"
    language: str = "English"
    recap_length: Literal["brief", "standard", "detailed"] = "standard"

class TranscriptChunkRequest(BaseModel):
    """Request to ingest a transcript chunk."""
    model_config = ConfigDict(extra="forbid")
    session_id: str
    text: str = Field(min_length=1)
    timestamp: str

class RecapRequest(BaseModel):
    """Request to generate a recap for a time window."""
    model_config = ConfigDict(extra="forbid")
    session_id: str
    from_timestamp: str
    to_timestamp: str

class SessionEndRequest(BaseModel):
    """Request to end a session."""
    model_config = ConfigDict(extra="forbid")
    session_id: str

class ExportRequest(BaseModel):
    """Request to export a session."""
    model_config = ConfigDict(extra="forbid")
    session_id: str

class AudioChunkRequest(BaseModel):
    """Request to ingest an audio chunk."""
    model_config = ConfigDict(extra="forbid")
    session_id: str
    chunk_index: int
    mime_type: str
    audio_base64: str
    timestamp: str
    source: str = "extension"

class NotionExportRequest(BaseModel):
    """Request to export a session to Notion."""
    model_config = ConfigDict(extra="forbid")
    session_id: str
    page_id: str
    notion_api_key: str | None = None

class StudyPackRequest(BaseModel):
    """Request to generate a study pack."""
    model_config = ConfigDict(extra="forbid")
    session_id: str

class APIStatusResponse(BaseModel):
    """Response."""
    status: str = "success"
    session_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    model_config = ConfigDict(populate_by_name=True)

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from services.jobs import bootstrap_system

@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    sys_manager = bootstrap_system()
    yield
    sys_manager.shutdown(wait=False)

app = fastapi.FastAPI(title="SnapBack API", version="0.1.0", lifespan=lifespan)
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
def start_session(payload: SessionStartRequest) -> object:
    res = start_op(payload.mode, payload.language, payload.recap_length)
    return {"session_id": res.get("id"), "start_timestamp": res.get("start_timestamp"), "session": res}

@app.post("/session/transcript")
def ingest_transcript(payload: TranscriptChunkRequest) -> object:
    return ingest_op(payload.session_id, payload.text, payload.timestamp)

@app.post("/session/audio-chunk")
def ingest_audio_chunk(payload: AudioChunkRequest) -> object:
    try:
        raw = base64.b64decode(payload.audio_base64)
    except Exception as error:
        raise fastapi.HTTPException(status_code=400, detail=f"Invalid payload: {error}") from error
    return save_op(payload.session_id, payload.chunk_index, payload.mime_type, raw, payload.timestamp, payload.source)

@app.post("/recap")
def generate_recap(payload: RecapRequest) -> object:
    return recap_op(payload.session_id, payload.from_timestamp, payload.to_timestamp)

@app.get("/session/{session_id}/transcript")
def get_session_transcript(session_id: str) -> object:
    return bundle_op(session_id)

@app.post("/session/end")
def complete_session(payload: SessionEndRequest) -> object:
    return end_op(payload.session_id)

@app.post("/export/pdf")
def export_pdf(payload: ExportRequest) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.pdf"'}
    return Response(content=pdf_op(payload.session_id), media_type="application/pdf", headers=headers)

@app.post("/export/markdown")
def export_markdown(payload: ExportRequest) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.md"'}
    return Response(content=md_op(payload.session_id), media_type="text/markdown", headers=headers)

@app.post("/export/notion")
def export_notion(payload: NotionExportRequest) -> object:
    return notion_op(payload.session_id, payload.page_id)

@app.post("/study/pack")
def generate_study_pack(payload: StudyPackRequest) -> object:
    return study_op(payload.session_id)
