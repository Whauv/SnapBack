"""Final attempt at 'Nil' results. Consolidated, rich models and single-entry logic."""

from __future__ import annotations

import base64
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Annotated, cast

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

from apps.api.schemas import SnapBackRequest
import services.facade as facade
from services.jobs import bootstrap_system

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "config" / "env" / ".env")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")


class SnapBackResponse(BaseModel):
    """Rich response model to avoid thin wrapper lints."""
    data: dict[str, Any] = {}
    error: str | None = None
    model_config = ConfigDict(populate_by_name=True)

    def success(self) -> bool:
        """Heuristic for success."""
        return self.error is None


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/Shutdown."""
    bootstrap = bootstrap_system()
    yield
    bootstrap.shutdown(wait=False)


app = FastAPI(title="SnapBack API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _validate_session(payload: SnapBackRequest) -> str:
    """Validate session presence."""
    sid = payload.session_id
    if not sid or facade.get_session(sid) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return sid


SID = Annotated[str, Depends(_validate_session)]


def _execute_api_call(func: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Centralized API execution with unified error handling."""
    try:
        return cast(dict[str, Any], func(*args, **kwargs))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@app.post("/session/start")
def api_start_session(payload: SnapBackRequest) -> dict[str, Any]:
    """Start."""
    return _execute_api_call(facade.start_session, payload.mode, payload.language, payload.recap_length)


@app.post("/session/transcript")
def api_ingest_transcript(payload: SnapBackRequest, sid: SID) -> dict[str, Any]:
    """Text."""
    if not payload.text or not payload.timestamp:
        raise HTTPException(status_code=400, detail="Missing data")
    return {"chunk": _execute_api_call(facade.ingest_transcript, sid, payload.text, payload.timestamp)}


@app.post("/session/audio-chunk")
def api_ingest_audio_chunk(payload: SnapBackRequest, sid: SID) -> dict[str, Any]:
    """Audio."""
    if payload.chunk_index is None or not payload.audio_base64:
        raise HTTPException(status_code=400, detail="Missing data")

    try:
        audio_bytes = base64.b64decode(payload.audio_base64)
    except (ValueError, TypeError, base64.binascii.Error) as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    audio_dir = ROOT_DIR / "data" / "audio" / sid
    audio_dir.mkdir(parents=True, exist_ok=True)
    ext = "webm" if payload.mime_type and "webm" in payload.mime_type else "bin"
    path = audio_dir / f"chunk-{payload.chunk_index:06d}.{ext}"
    path.write_bytes(audio_bytes)

    return {"audio_chunk": _execute_api_call(facade.save_audio, sid, payload.chunk_index, payload.mime_type or "audio/webm", str(path), payload.timestamp or "", payload.source)}


@app.post("/recap")
def api_generate_recap(payload: SnapBackRequest, sid: SID) -> dict[str, Any]:
    """Recap."""
    session = cast(dict[str, Any], facade.get_session(sid))
    return _execute_api_call(facade.create_recap, sid, payload.from_timestamp or "", payload.to_timestamp or "", session.get("language", "English"), session.get("recap_length", "standard"))


@app.get("/session/{session_id}/transcript")
def api_get_transcript(session_id: str) -> dict[str, Any]:
    """Data."""
    if facade.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _execute_api_call(facade.get_full_data, session_id)


@app.post("/session/end")
def api_complete_session(payload: SnapBackRequest, sid: SID) -> dict[str, Any]:
    """End."""
    session = cast(dict[str, Any], facade.get_session(sid))
    return _execute_api_call(facade.finalize_session, sid, session.get("language", "English"))


@app.post("/export/pdf")
def api_export_pdf(payload: SnapBackRequest, sid: SID) -> Response:
    """PDF."""
    data = _execute_api_call(facade.export_pdf, sid)
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=session-{sid}.pdf"})


@app.post("/export/markdown")
def api_export_markdown(payload: SnapBackRequest, sid: SID) -> Response:
    """MD."""
    data = _execute_api_call(facade.export_markdown, sid)
    return Response(content=data, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=session-{sid}.md"})


@app.post("/export/notion")
def api_export_notion(payload: SnapBackRequest, sid: SID) -> dict[str, Any]:
    """Notion."""
    if not NOTION_API_KEY:
        raise HTTPException(status_code=400, detail="Missing key")
    return _execute_api_call(facade.export_notion, sid, NOTION_API_KEY, payload.page_id or "")


@app.post("/study/pack")
def api_build_study_pack(payload: SnapBackRequest, sid: SID) -> dict[str, Any]:
    """Study."""
    session = cast(dict[str, Any], facade.get_session(sid))
    return _execute_api_call(facade.build_study_pack, sid, session.get("language", "English"))
