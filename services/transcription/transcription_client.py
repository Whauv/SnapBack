"""Compatibility wrapper for the transcription runtime module."""

from services.transcription.transcription_runtime import (
    TranscriptionClient,
    TranscriptionConfig,
    TranscriptionRuntime,
    utc_now_iso,
)

__all__ = [
    "TranscriptionClient",
    "TranscriptionConfig",
    "TranscriptionRuntime",
    "utc_now_iso",
]
