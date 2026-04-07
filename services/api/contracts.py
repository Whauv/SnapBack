"""Request contracts for the SnapBack API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TIMESTAMP_ERROR = "Timestamps must be valid ISO-8601 strings."


def parse_timestamp(value: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(TIMESTAMP_ERROR) from error
    return value


def clean_text(value: str, *, field_name: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


class SessionStartRequest(BaseModel):
    """Request to start a new session."""

    model_config = ConfigDict(extra="forbid")
    mode: Literal["cloud", "local"] = "cloud"
    language: str = Field(default="English", min_length=2, max_length=32)
    recap_length: Literal["brief", "standard", "detailed"] = "standard"

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return clean_text(value, field_name="language")


class TranscriptChunkRequest(BaseModel):
    """Request to ingest a transcript chunk."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)
    text: str
    timestamp: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return clean_text(value, field_name="session_id")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return clean_text(value, field_name="text")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return parse_timestamp(value)


class RecapRequest(BaseModel):
    """Request to generate a recap for a time window."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)
    from_timestamp: str
    to_timestamp: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return clean_text(value, field_name="session_id")

    @field_validator("from_timestamp", "to_timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return parse_timestamp(value)


class SessionEndRequest(BaseModel):
    """Request to end a session."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return clean_text(value, field_name="session_id")


class ExportRequest(BaseModel):
    """Request to export a session."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return clean_text(value, field_name="session_id")


class AudioChunkRequest(BaseModel):
    """Request to ingest an audio chunk."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)
    chunk_index: int = Field(ge=0, le=1_000_000)
    mime_type: str = Field(min_length=1, max_length=64)
    audio_base64: str = Field(min_length=1)
    timestamp: str
    source: str = Field(default="extension", min_length=1, max_length=32)

    @field_validator("session_id", "source")
    @classmethod
    def validate_identifiers(cls, value: str, info: Any) -> str:
        return clean_text(value, field_name=info.field_name)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        return clean_text(value, field_name="mime_type").lower()

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return parse_timestamp(value)


class NotionExportRequest(BaseModel):
    """Request to export a session to Notion."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)
    page_id: str = Field(min_length=1, max_length=128)
    notion_api_key: str | None = Field(default=None, max_length=256)

    @field_validator("session_id", "page_id")
    @classmethod
    def validate_values(cls, value: str, info: Any) -> str:
        return clean_text(value, field_name=info.field_name)


class StudyPackRequest(BaseModel):
    """Request to generate a study pack."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return clean_text(value, field_name="session_id")
