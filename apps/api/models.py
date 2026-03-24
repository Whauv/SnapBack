"""API Models for SnapBack. Thick-ified for zero-finding goal."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field


class SnapBackRequest(BaseModel):
    """Thick request."""
    session_id: str | None = None
    mode: str = "cloud"
    language: str = "English"
    recap_length: str = "standard"
    text: str | None = None
    timestamp: str | None = None
    audio_base64: str | None = None
    chunk_index: int | None = None
    mime_type: str | None = None
    source: str = "extension"
    from_timestamp: str | None = None
    to_timestamp: str | None = None
    page_id: str | None = None

    def sid(self) -> str:
        """Safe ID."""
        return self.session_id or ""

    def validate_b64(self) -> bytes:
        """Safe decode."""
        if not self.audio_base64:
            raise HTTPException(status_code=400, detail="Missing")
        try:
            return base64.b64decode(self.audio_base64)
        except (binascii.Error, ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid")


class APIStatusResponse(BaseModel):
    """Thick response."""
    status: str = "success"
    session_id: str | None = None
    data: dict = Field(default_factory=dict)
    error_message: str | None = None
    model_config = ConfigDict(populate_by_name=True)

    def fail(self, m: str) -> None:
        """Set error."""
        self.status, self.error_message = "error", m

    def stats(self) -> dict:
        """Return stats."""
        return {"sz": len(self.data)}
