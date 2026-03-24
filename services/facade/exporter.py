"""Exporter-related facade functions."""

from __future__ import annotations
from typing import Any, cast
from services.exporters.export import (
    build_markdown_export,
    build_pdf_export,
    export_to_notion,
)
from services.storage import database
from services.constants import ERR_SESSION_NOT_FOUND

def _get_bundle_or_raise(sid: str) -> dict[str, Any]:
    """Ensure session exists and return bundle."""
    bundle = database.get_session_bundle(sid)
    if not bundle:
        raise ValueError(ERR_SESSION_NOT_FOUND)
    return cast(dict[str, Any], bundle)

def export_pdf(sid: str) -> bytes:
    """Build PDF."""
    return build_pdf_export(_get_bundle_or_raise(sid))

def export_markdown(sid: str) -> str:
    """Build Markdown."""
    return build_markdown_export(_get_bundle_or_raise(sid))

def export_notion(sid: str, api_key: str, page_id: str) -> dict[str, Any]:
    """To Notion."""
    return export_to_notion(_get_bundle_or_raise(sid), api_key=api_key, page_id=page_id)

def get_full_data(sid: str) -> dict[str, Any]:
    """Get all session data."""
    bundle = _get_bundle_or_raise(sid)
    return {
        "session": cast(dict[str, Any], bundle.get("session")),
        "transcript": [cast(dict[str, Any], t) for t in bundle.get("transcript", [])],
        "recaps": [cast(dict[str, Any], r) for r in bundle.get("recaps", [])],
    }
