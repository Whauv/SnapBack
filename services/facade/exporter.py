"""Exporter facade with zero findings goal."""

from __future__ import annotations
from services.exporters.export import (
    build_markdown_export,
    build_pdf_export,
    export_to_notion,
)
from services.constants import ERR_SESSION_NOT_FOUND
from services.storage.database import SessionBundle, SnapBackStorage


def _get_bundle(sid: str) -> SessionBundle:
    """Ensure session exists and return full bundle; raises ValueError on failure."""
    bundle = SnapBackStorage().get_bundle(sid)
    if not bundle:
        raise ValueError(ERR_SESSION_NOT_FOUND)
    return bundle


def generate_pdf(sid: str) -> bytes:
    """Generate binary PDF export."""
    return build_pdf_export(_get_bundle(sid))


def generate_md(sid: str) -> str:
    """Generate text MD export."""
    return build_markdown_export(_get_bundle(sid))


def send_to_notion(sid: str, api_key: str, page_id: str) -> dict:
    """Perform Notion export."""
    return export_to_notion(_get_bundle(sid), api_key=api_key, page_id=page_id)


def get_bundle_data(sid: str) -> dict:
    """Retrieve full data bundle."""
    return _get_bundle(sid).model_dump()
