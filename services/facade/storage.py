"""Storage-related facade functions."""

from __future__ import annotations
from typing import Any, cast
from services.storage import database

def start_session(mode: str, lang: str, recap: str) -> dict[str, Any]:
    """Start a session."""
    return cast(dict[str, Any], database.create_session(mode, lang, recap))

def get_session(sid: str) -> dict[str, Any] | None:
    """Get meta."""
    return cast(dict[str, Any], database.get_session(sid)) if database.get_session(sid) else None

def ingest_transcript(sid: str, text: str, ts: str) -> dict[str, Any]:
    """Save chunk."""
    return cast(dict[str, Any], database.append_transcript_chunk(sid, text, ts))

def save_audio(sid: str, idx: int, mime: str, path: str, ts: str, src: str) -> dict[str, Any]:
    """Save audio meta."""
    return cast(dict[str, Any], database.save_audio_chunk(
        session_id=sid, chunk_index=idx, mime_type=mime,
        file_path=path, timestamp=ts, source=src
    ))
