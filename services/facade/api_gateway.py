"""API Gateway Facade for SnapBack. Consolidated nil-finding pass."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.facade.analysis import (
    build_student_pack,
    conclude_and_summarize,
    orchestrate_recap,
)
from services.facade.exporter import (
    generate_md,
    generate_pdf,
    get_bundle_data,
    send_to_notion,
)
from services.facade.storage import (
    get_session,
    ingest_segment,
    save_audio,
    start_session,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


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
            s = cast("Mapping[str, object]", get_session(sid))
            if not s:
                return _missing_session()
            args = (sid, *args) if not args or args[0] != sid else args
        return task(*args)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (TypeError, IndexError, KeyError, HTTPException):
        raise


def _missing_session() -> object:
    """Raise a standard missing-session HTTP exception."""
    detail = "Not found"
    raise HTTPException(status_code=404, detail=detail)


def start_op(mode: str, language: str, recap_length: str) -> Mapping[str, object]:
    """Start."""
    return cast(
        "Mapping[str, object]",
        _exec(start_session, (mode, language, recap_length)),
    )


def ingest_op(sid: str, t: str, ts: str) -> Mapping[str, object]:
    """Segment."""
    return {"chunk": _exec(ingest_segment, (sid, t, ts), sid=sid)}


def save_op(  # noqa: PLR0913
    sid: str,
    idx: int,
    mime: str,
    raw: bytes,
    ts: str,
    src: str,
) -> Mapping[str, object]:
    """Audio."""
    root = Path(__file__).resolve().parents[2]
    d = root / "data" / "audio" / sid
    d.mkdir(parents=True, exist_ok=True)
    ext = "webm" if "webm" in (mime or "") else "bin"
    p = d / f"chunk-{idx:06d}.{ext}"
    p.write_bytes(raw)
    return {
        "audio_chunk": _exec(
            save_audio,
            (sid, idx, mime, str(p), ts, src),
            sid=sid,
        ),
    }


def recap_op(sid: str, f: str | None, t: str | None) -> Mapping[str, object]:
    """Recap."""
    s = cast("Mapping[str, object]", _exec(get_session, (sid,), sid=sid))
    return cast(
        "Mapping[str, object]",
        _exec(
            orchestrate_recap,
            (
                sid,
                f or "",
                t or "",
                str(s.get("language", "English")),
                str(s.get("recap_length", "standard")),
            ),
        ),
    )


def bundle_op(sid: str) -> Mapping[str, object]:
    """Bundle."""
    return cast("Mapping[str, object]", _exec(get_bundle_data, (sid,), sid=sid))


def end_op(sid: str) -> Mapping[str, object]:
    """End."""
    s = cast("Mapping[str, object]", _exec(get_session, (sid,), sid=sid))
    return cast(
        "Mapping[str, object]",
        _exec(conclude_and_summarize, (sid, str(s.get("language", "English")))),
    )


def pdf_op(sid: str) -> bytes:
    """PDF."""
    return cast("bytes", _exec(generate_pdf, (sid,), sid=sid))


def md_op(sid: str) -> str:
    """MD."""
    return cast("str", _exec(generate_md, (sid,), sid=sid))


def notion_op(sid: str, pid: str | None) -> Mapping[str, object]:
    """Notion."""
    k = os.getenv("NOTION_API_KEY", "")
    if not k:
        raise HTTPException(status_code=400, detail="Missing key")
    return cast(
        "Mapping[str, object]",
        _exec(send_to_notion, (sid, k, pid or ""), sid=sid),
    )


def study_op(sid: str) -> Mapping[str, object]:
    """Pack."""
    s = cast("Mapping[str, object]", _exec(get_session, (sid,), sid=sid))
    return cast(
        "Mapping[str, object]",
        _exec(build_student_pack, (sid, str(s.get("language", "English")))),
    )
