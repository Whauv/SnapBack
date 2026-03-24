"""Analysis-related facade functions."""

from __future__ import annotations
from typing import Any, cast
from services.analysis import summarizer
from services.analysis.detector import detect_missed_alerts, detect_topic_shift
from services.storage import database
from services.constants import ERR_SESSION_NOT_FOUND

def create_recap(sid: str, from_ts: str, to_ts: str, lang: str, recap: str) -> dict[str, Any]:
    """Generate summary and detect shifts."""
    chunks = database.get_transcript_window(sid, from_ts, to_ts)
    if not chunks:
        raise ValueError(ERR_SESSION_NOT_FOUND)

    text = "\n".join(c["text"] for c in chunks)
    summary = summarizer.generate_summary(text, lang, recap)
    keywords = summarizer.extract_keywords(text)

    prev = database.get_last_chunk_before(sid, from_ts)
    curr = database.get_first_chunk_after(sid, to_ts) or (chunks[-1] if chunks else None)
    shift = detect_topic_shift(prev["text"] if prev else None, curr["text"] if curr else None)

    alerts = [cast(dict[str, Any], a) for a in detect_missed_alerts(chunks)]

    recap_data = database.save_recap(
        session_id=sid, from_timestamp=from_ts, to_timestamp=to_ts,
        summary=summary, keywords=keywords,
        topic_shift_detected=shift, missed_alerts=alerts
    )
    return {"summary": summary, "keywords": keywords, "recap": cast(dict[str, Any], recap_data)}

def finalize_session(sid: str, lang: str) -> dict[str, Any]:
    """Finalize session."""
    transcript = database.get_transcript(sid)
    text = "\n".join(c["text"] for c in transcript)
    summary = summarizer.summarize_full_session(text, lang)
    updated = database.end_session(sid, summary)
    return {"full_summary": summary, "session": cast(dict[str, Any], updated)}

def build_study_pack(sid: str, lang: str) -> dict[str, Any]:
    """Generate study materials."""
    bundle = database.get_session_bundle(sid)
    if not bundle:
        raise ValueError(ERR_SESSION_NOT_FOUND)
    text = "\n".join(c["text"] for c in bundle["transcript"])
    pack = summarizer.generate_study_pack(text, lang)
    return {"session_id": sid, "study_pack": cast(dict[str, Any], pack)}
