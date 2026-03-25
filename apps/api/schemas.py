"""Request and response schemas for the SnapBack API."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Callable, Sequence
from typing import Annotated, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from services.analysis.engine import EngineStudyPack
from services.storage.database import AudioChunk, Recap, Session, TranscriptChunk

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Mode = Literal["cloud", "local"]
RecapLength = Literal["brief", "standard", "detailed"]
ParsedT = TypeVar("ParsedT")


def _require_mapping(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    message = f"{field_name} must be an object"
    raise ValueError(message)


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        message = f"{field_name} must be text"
        raise TypeError(message)
    cleaned = value.strip()
    if not cleaned:
        message = f"{field_name} cannot be blank"
        raise ValueError(message)
    return cleaned


def _parse_items(
    value: object,
    field_name: str,
    parse_item: Callable[[object, str], ParsedT],
) -> list[ParsedT]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        message = f"{field_name} must be a list"
        raise TypeError(message)
    return [parse_item(item, field_name) for item in value]


class SessionRequest(BaseModel):
    """Request body shared by the session endpoints with compatible fields."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    session_id: NonBlankText | None = None
    mode: Mode = "cloud"
    language: NonBlankText = "English"
    recap_length: RecapLength = "standard"
    text: NonBlankText | None = None
    timestamp: NonBlankText | None = None
    page_id: NonBlankText | None = None

    def _require_value(self, value: NonBlankText | None, field_name: str) -> str:
        """Return a required non-empty field value."""
        if value is None:
            message = f"{field_name} is required"
            raise ValueError(message)
        return value

    def session(self) -> str:
        """Return the validated session id."""
        return self._require_value(self.session_id, "session_id")

    def start_args(self) -> tuple[Mode, str, RecapLength]:
        """Return normalized arguments for session start."""
        return self.mode, self.language, self.recap_length

    def transcript_args(self) -> tuple[str, str, str]:
        """Return normalized arguments for transcript ingestion."""
        return (
            self.session(),
            self._require_value(self.text, "text"),
            self._require_value(self.timestamp, "timestamp"),
        )

    def notion_args(self) -> tuple[str, str]:
        """Return normalized arguments for Notion export."""
        return self.session(), self._require_value(self.page_id, "page_id")


class AudioChunkRequest(BaseModel):
    """Request body for audio ingestion."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    session_id: NonBlankText
    chunk_index: int = Field(ge=0)
    mime_type: NonBlankText
    audio_base64: NonBlankText
    timestamp: NonBlankText
    source: NonBlankText = "extension"

    def audio_args(self) -> tuple[str, int, str, bytes, str, str]:
        """Decode and return normalized arguments for audio ingestion."""
        try:
            raw = base64.b64decode(self.audio_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            message = f"Invalid base64 audio payload: {exc}"
            raise ValueError(message) from exc
        return (
            self.session_id,
            self.chunk_index,
            self.mime_type,
            raw,
            self.timestamp,
            self.source,
        )


class RecapRequest(BaseModel):
    """Request body for recap generation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    session_id: NonBlankText
    from_timestamp: NonBlankText
    to_timestamp: NonBlankText

    @model_validator(mode="after")
    def validate_window(self) -> RecapRequest:
        """Ensure the requested recap time window is valid."""
        if self.from_timestamp >= self.to_timestamp:
            message = "from_timestamp must be earlier than to_timestamp"
            raise ValueError(message)
        return self

    def recap_args(self) -> tuple[str, str, str]:
        """Return normalized arguments for recap generation."""
        return self.session_id, self.from_timestamp, self.to_timestamp


class SnapBackResponse(BaseModel):
    """Unified typed response for all SnapBack API operations."""

    model_config = ConfigDict(populate_by_name=True)

    status: Literal["success", "ok"] = "success"
    session_id: str | None = None
    start_timestamp: str | None = None
    session: Session | None = None
    chunk: TranscriptChunk | None = None
    audio_chunk: AudioChunk | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    recap: Recap | None = None
    transcript: list[TranscriptChunk] = Field(default_factory=list)
    recaps: list[Recap] = Field(default_factory=list)
    full_summary: str | None = None
    study_pack: EngineStudyPack | None = None
    page_id: str | None = None
    url: str | None = None

    @classmethod
    def health(cls: type[SnapBackResponse]) -> SnapBackResponse:
        """Return a health-check response."""
        return cls(status="ok")

    @classmethod
    def _from_start(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a session start payload."""
        session = Session.model_validate(payload)
        return cls(
            session_id=session.id,
            start_timestamp=session.start_timestamp,
            session=session,
        )

    @classmethod
    def _from_transcript(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a transcript payload."""
        raw_chunk = _require_mapping(payload.get("chunk"), "chunk")
        return cls(chunk=TranscriptChunk.model_validate(raw_chunk))

    @classmethod
    def _from_audio(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from an audio payload."""
        raw_chunk = _require_mapping(payload.get("audio_chunk"), "audio_chunk")
        return cls(audio_chunk=AudioChunk.model_validate(raw_chunk))

    @classmethod
    def _from_recap(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a recap payload."""
        raw_recap = _require_mapping(payload.get("recap"), "recap")
        return cls(
            summary=_require_text(payload.get("summary", ""), "summary"),
            keywords=_parse_items(
                payload.get("keywords", []),
                "keywords",
                _require_text,
            ),
            recap=Recap.model_validate(raw_recap),
        )

    @classmethod
    def _from_bundle(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a bundle payload."""
        transcript = [
            TranscriptChunk.model_validate(item)
            for item in _parse_items(
                payload.get("transcript", []),
                "transcript",
                _require_mapping,
            )
        ]
        recaps = [
            Recap.model_validate(item)
            for item in _parse_items(
                payload.get("recaps", []),
                "recaps",
                _require_mapping,
            )
        ]
        session = Session.model_validate(
            _require_mapping(payload.get("session"), "session"),
        )
        return cls(
            session_id=session.id,
            session=session,
            transcript=transcript,
            recaps=recaps,
        )

    @classmethod
    def _from_end(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a session end payload."""
        session = Session.model_validate(
            _require_mapping(payload.get("session"), "session"),
        )
        return cls(
            session_id=session.id,
            full_summary=_require_text(payload.get("full_summary", ""), "full_summary"),
            session=session,
        )

    @classmethod
    def _from_notion(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a Notion export payload."""
        return cls(
            page_id=_require_text(payload.get("page_id", ""), "page_id"),
            url=_require_text(payload.get("url", ""), "url"),
        )

    @classmethod
    def _from_study_pack(
        cls: type[SnapBackResponse], payload: dict[str, object],
    ) -> SnapBackResponse:
        """Build a response from a study-pack payload."""
        session_id = _require_text(payload.get("session_id", ""), "session_id")
        study_pack = EngineStudyPack.model_validate(
            _require_mapping(payload.get("study_pack"), "study_pack"),
        )
        return cls(session_id=session_id, study_pack=study_pack)

    def export_filename(self, extension: str) -> str:
        """Return a deterministic export filename."""
        return f"snapback-{self.session_id or 'export'}.{extension}"

    def total_words(self) -> int:
        """Return the total transcript word count in this response."""
        return sum(chunk.wc() for chunk in self.transcript)

    def has_payload(self) -> bool:
        """Return True when the response contains any domain payload."""
        return any(
            [
                self.session is not None,
                self.chunk is not None,
                self.audio_chunk is not None,
                self.recap is not None,
                bool(self.transcript),
                bool(self.recaps),
                self.study_pack is not None,
                self.url is not None,
            ],
        )
