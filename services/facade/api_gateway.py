"""API Gateway Facade for SnapBack. Consolidated nil-finding pass."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import cast, Callable, Mapping

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.facade.storage import start_session, get_session, ingest_segment, save_audio
from services.facade.analysis import orchestrate_recap, conclude_and_summarize, build_student_pack
from services.facade.exporter import generate_pdf, generate_md, send_to_notion, get_bundle_data


class RESP(BaseModel):
    """Thick response."""
    status: str = "success"
    session_id: str | None = None
    data: dict = Field(default_factory=dict)
    error_message: str | None = None
    model_config = ConfigDict(populate_by_name=True)

    def set_err(self, msg: str) -> None:
        """Indicate failure."""
        self.status, self.error_message = "error", msg

    def clear(self) -> None:
        """Reset data."""
        self.data = {}


def _exec(task: Callable, args: tuple, sid: str | None = None) -> object:
    """Consolidated executor with integrated validation to eliminate duplicates."""
    try:
        if sid:
            s = cast(Mapping[str, object], get_session(sid))
            if not s:
                raise HTTPException(status_code=404, detail="Not found")
            args = (sid,) + args if not args or args[0] != sid else args
        return task(*args)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (TypeError, IndexError, KeyError, HTTPException):
        raise


def start_op(m: str, l: str, r: str) -> Mapping[str, object]:
    """Start."""
    return cast(Mapping[str, object], _exec(start_session, (m, l, r)))


def ingest_op(sid: str, t: str, ts: str) -> Mapping[str, object]:
    """Segment."""
    return {"chunk": _exec(ingest_segment, (sid, t, ts), sid=sid)}


def save_op(sid: str, idx: int, mime: str, raw: bytes, ts: str, src: str) -> Mapping[str, object]:
    """Audio."""
    root = Path(__file__).resolve().parents[2]
    d = root / "data" / "audio" / sid
    d.mkdir(parents=True, exist_ok=True)
    ext = "webm" if "webm" in (mime or "") else "bin"
    p = d / f"chunk-{idx:06d}.{ext}"
    p.write_bytes(raw)
    return {"audio_chunk": _exec(save_audio, (sid, idx, mime, str(p), ts, src), sid=sid)}


def recap_op(sid: str, f: str | None, t: str | None) -> Mapping[str, object]:
    """Recap."""
    s = cast(Mapping[str, object], _exec(get_session, (sid,), sid=sid))
    return cast(Mapping[str, object], _exec(orchestrate_recap, (sid, f or "", t or "", str(s.get("language", "English")), str(s.get("recap_length", "standard")))))


def bundle_op(sid: str) -> Mapping[str, object]:
    """Bundle."""
    return cast(Mapping[str, object], _exec(get_bundle_data, (sid,), sid=sid))


def end_op(sid: str) -> Mapping[str, object]:
    """End."""
    s = cast(Mapping[str, object], _exec(get_session, (sid,), sid=sid))
    return cast(Mapping[str, object], _exec(conclude_and_summarize, (sid, str(s.get("language", "English")))))


def pdf_op(sid: str) -> bytes:
    """PDF."""
    return cast(bytes, _exec(generate_pdf, (sid,), sid=sid))


def md_op(sid: str) -> str:
    """MD."""
    return cast(str, _exec(generate_md, (sid,), sid=sid))


def notion_op(sid: str, pid: str | None) -> Mapping[str, object]:
    """Notion."""
    k = os.getenv("NOTION_API_KEY", "")
    if not k:
        raise HTTPException(status_code=400, detail="Missing key")
    return cast(Mapping[str, object], _exec(send_to_notion, (sid, k, pid or ""), sid=sid))


def study_op(sid: str) -> Mapping[str, object]:
    """Pack."""
    s = cast(Mapping[str, object], _exec(get_session, (sid,), sid=sid))
    return cast(Mapping[str, object], _exec(build_student_pack, (sid, str(s.get("language", "English")))))
