"""Application service layer for SnapBack session workflows."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.analysis.detector import detect_missed_alerts, detect_topic_shift
from services.analysis.summarizer import GroqSummarizer
from services.api.auth import AuthenticatedPrincipal
from services.api.settings import AppSettings
from services.exporters.export import (
    build_markdown_export,
    build_pdf_export,
    export_to_notion,
)
from services.storage.database import (
    append_transcript_chunk,
    create_session,
    end_session,
    get_first_chunk_after,
    get_last_chunk_before,
    get_recaps,
    get_session,
    get_session_bundle,
    get_transcript,
    get_transcript_window,
    save_audio_chunk,
    save_recap,
)

SUPPORTED_AUDIO_MIME_TYPES = {"audio/webm", "audio/wav", "audio/mp4", "application/octet-stream"}


@dataclass
class SessionService:
    root_dir: Path
    settings: AppSettings
    summarizer: GroqSummarizer

    def _get_owned_session(self, session_id: str, principal: AuthenticatedPrincipal) -> dict[str, Any]:
        session = get_session(session_id, owner_id=principal.principal_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def _get_owned_bundle(self, session_id: str, principal: AuthenticatedPrincipal):
        bundle = get_session_bundle(session_id, owner_id=principal.principal_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="Session not found")
        return bundle

    @staticmethod
    def _extension_for_mime_type(mime_type: str) -> str:
        return {
            "audio/webm": "webm",
            "audio/wav": "wav",
            "audio/mp4": "mp4",
            "application/octet-stream": "bin",
        }.get(mime_type, "bin")

    def start_session(self, *, principal: AuthenticatedPrincipal, mode: str, language: str, recap_length: str) -> dict[str, Any]:
        session = create_session(
            owner_id=principal.principal_id,
            mode=mode,
            language=language,
            recap_length=recap_length,
        )
        return {"session_id": session["id"], "start_timestamp": session["start_timestamp"], "session": session}

    def ingest_transcript(self, *, principal: AuthenticatedPrincipal, session_id: str, text: str, timestamp: str) -> dict[str, Any]:
        self._get_owned_session(session_id, principal)
        if len(text) > self.settings.max_transcript_chars:
            raise HTTPException(status_code=413, detail="Transcript chunk exceeds the configured size limit.")
        chunk = append_transcript_chunk(session_id, text, timestamp)
        return {"chunk": chunk}

    def ingest_audio_chunk(
        self,
        *,
        principal: AuthenticatedPrincipal,
        session_id: str,
        chunk_index: int,
        mime_type: str,
        audio_base64: str,
        timestamp: str,
        source: str,
    ) -> dict[str, Any]:
        self._get_owned_session(session_id, principal)
        if mime_type not in SUPPORTED_AUDIO_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported audio mime_type.")

        try:
            audio_bytes = base64.b64decode(audio_base64, validate=True)
        except Exception as error:
            raise HTTPException(status_code=400, detail=f"Invalid audio payload: {error}") from error

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio payload cannot be empty.")
        if len(audio_bytes) > self.settings.max_audio_chunk_bytes:
            raise HTTPException(status_code=413, detail="Audio payload exceeds the configured size limit.")

        audio_dir = self.root_dir / "data" / "audio" / session_id
        audio_dir.mkdir(parents=True, exist_ok=True)
        extension = self._extension_for_mime_type(mime_type)
        file_path = audio_dir / f"chunk-{chunk_index:06d}.{extension}"
        file_path.write_bytes(audio_bytes)

        chunk = save_audio_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            mime_type=mime_type,
            file_path=str(file_path),
            timestamp=timestamp,
            source=source,
        )
        return {"audio_chunk": chunk}

    def generate_recap(
        self,
        *,
        principal: AuthenticatedPrincipal,
        session_id: str,
        from_timestamp: str,
        to_timestamp: str,
    ) -> dict[str, Any]:
        session = self._get_owned_session(session_id, principal)
        if from_timestamp > to_timestamp:
            raise HTTPException(status_code=400, detail="from_timestamp must be earlier than to_timestamp.")

        chunks = get_transcript_window(session_id, from_timestamp, to_timestamp)
        transcript_text = "\n".join(chunk["text"] for chunk in chunks)
        summary = self.summarizer.generate_summary(
            transcript_text,
            language=session.get("language", "English"),
            recap_length=session.get("recap_length", "standard"),
        )
        keywords = self.summarizer.extract_keywords(transcript_text)
        previous_chunk = get_last_chunk_before(session_id, from_timestamp)
        current_chunk = get_first_chunk_after(session_id, to_timestamp)
        comparison_chunk = current_chunk or (chunks[-1] if chunks else None) or (chunks[0] if chunks else None)
        topic_shift_detected = detect_topic_shift(
            previous_chunk["text"] if previous_chunk else None,
            comparison_chunk["text"] if comparison_chunk else None,
        )
        missed_alerts = detect_missed_alerts(chunks)
        recap = save_recap(
            session_id=session_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            summary=summary,
            keywords=keywords,
            topic_shift_detected=topic_shift_detected,
            missed_alerts=missed_alerts,
        )
        return {
            "summary": summary,
            "keywords": keywords,
            "topic_shift_detected": topic_shift_detected,
            "missed_alerts": missed_alerts,
            "topic_shift_reference": {
                "before_departure": previous_chunk["timestamp"] if previous_chunk else None,
                "comparison_chunk": comparison_chunk["timestamp"] if comparison_chunk else None,
            },
            "recap": recap,
        }

    def get_session_transcript(self, *, principal: AuthenticatedPrincipal, session_id: str) -> dict[str, Any]:
        session = self._get_owned_session(session_id, principal)
        return {"session": session, "transcript": get_transcript(session_id), "recaps": get_recaps(session_id)}

    def complete_session(self, *, principal: AuthenticatedPrincipal, session_id: str) -> dict[str, Any]:
        session = self._get_owned_session(session_id, principal)
        transcript = get_transcript(session_id)
        transcript_text = "\n".join(chunk["text"] for chunk in transcript)
        full_summary = self.summarizer.summarize_full_session(
            transcript_text,
            language=session.get("language", "English"),
        )
        updated_session = end_session(session_id, full_summary)
        return {"full_summary": full_summary, "session": updated_session}

    def export_pdf(self, *, principal: AuthenticatedPrincipal, session_id: str) -> bytes:
        bundle = self._get_owned_bundle(session_id, principal)
        return build_pdf_export({"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps})

    def export_markdown(self, *, principal: AuthenticatedPrincipal, session_id: str) -> str:
        bundle = self._get_owned_bundle(session_id, principal)
        return build_markdown_export({"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps})

    def export_notion(
        self,
        *,
        principal: AuthenticatedPrincipal,
        session_id: str,
        page_id: str,
        notion_api_key: str | None,
    ) -> dict[str, Any]:
        bundle = self._get_owned_bundle(session_id, principal)
        api_key = notion_api_key or self.settings.notion_api_key
        if not api_key:
            raise HTTPException(status_code=400, detail="Missing Notion API key")
        return export_to_notion(
            {"session": bundle.session, "transcript": bundle.transcript, "recaps": bundle.recaps},
            api_key=api_key,
            page_id=page_id,
        )

    def generate_study_pack(self, *, principal: AuthenticatedPrincipal, session_id: str) -> dict[str, Any]:
        bundle = self._get_owned_bundle(session_id, principal)
        transcript_text = "\n".join(chunk["text"] for chunk in bundle.transcript)
        study_pack = self.summarizer.generate_study_pack(
            transcript_text,
            language=bundle.session.get("language", "English"),
        )
        return {"session_id": session_id, "study_pack": study_pack}
