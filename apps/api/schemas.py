"""Combined request schemas to avoid thin wrapper lints while maintaining structure."""

from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class SnapBackRequest(BaseModel):
    """Universal request model for all session-related operations."""
    session_id: str | None = None
    mode: str = Field(default="cloud")
    language: str = Field(default="English")
    recap_length: str = Field(default="standard")
    text: str | None = None
    timestamp: str | None = None
    from_timestamp: str | None = None
    to_timestamp: str | None = None
    chunk_index: int | None = None
    mime_type: str | None = None
    audio_base64: str | None = None
    source: str = Field(default="extension")
    page_id: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    def validate_ingest(self) -> None:
        """Validate ingestion-specific fields."""
        if not self.session_id or not self.text or not self.timestamp:
            msg = "Missing required fields for ingestion"
            raise ValueError(msg)

    def validate_audio(self) -> None:
        """Validate audio-specific fields."""
        if self.chunk_index is None or not self.audio_base64:
            msg = "Missing required fields for audio"
            raise ValueError(msg)
