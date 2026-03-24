"""Storage facade using rich models and bare dict."""

from __future__ import annotations
from services.storage.database import SnapBackStorage

def start_session(mode: str, lang: str, recap: str) -> dict:
    """Initialize session."""
    return SnapBackStorage().create_session(mode, lang, recap).model_dump()

def get_session(sid: str) -> dict | None:
    """Fetch session."""
    s = SnapBackStorage().get_session(sid)
    return s.model_dump() if s else None

def ingest_segment(sid: str, text: str, ts: str) -> dict:
    """Record segment."""
    return SnapBackStorage().append_chunk(sid, text, ts).model_dump()

def save_audio(sid: str, idx: int, mime: str, path: str, ts: str, src: str) -> dict:
    """Record audio."""
    return SnapBackStorage().save_audio(sid, idx, mime, path, ts, src).model_dump()
