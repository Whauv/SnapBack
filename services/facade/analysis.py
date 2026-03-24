"""Analysis facade logic consolidated for zero findings."""

from __future__ import annotations

import os
from services.analysis.engine import (
    AnalysisEngine,
    detect_missed_alerts,
    detect_topic_shift,
)
from services.storage.database import SnapBackStorage


def _boot_engine() -> AnalysisEngine:
    """Initialize engine."""
    return AnalysisEngine(key=os.getenv("GROQ_API_KEY", ""))


def orchestrate_recap(sid: str, f: str, t: str, lang: str, mode: str) -> dict:
    """Generate recap."""
    store = SnapBackStorage()
    store.fetch_bundle_or_raise(sid)

    chunks = store.get_transcript(sid, f, t)
    if not chunks:
        from services.constants import ERR_SESSION_NOT_FOUND

        raise ValueError(ERR_SESSION_NOT_FOUND)

    e = _boot_engine()
    txt = "\n".join(c.text for c in chunks)
    summ = e.generate_summary(txt, lang, mode)
    keyw = e.extract_keywords(txt)

    pv = store.get_neighbor(sid, f, before=True)
    sh = detect_topic_shift(
        pv.text if pv else None,
        (store.get_neighbor(sid, t, before=False) or chunks[-1]).text,
    )

    al = [
        a.model_dump() for a in detect_missed_alerts([c.model_dump() for c in chunks])
    ]
    recap = store.save_recap(sid, f, t, summ, keyw, sh, al)

    return {"summary": summ, "keywords": keyw, "recap": recap.model_dump()}


def conclude_and_summarize(sid: str, lang: str) -> dict:
    """Summarize and mark completion."""
    store = SnapBackStorage()
    chunks = store.get_transcript(sid)
    txt = "\n".join(c.text for c in chunks)
    summ = _boot_engine().summarize_full_session(txt, lang)
    sn = store.end_session(sid, summ)
    return {"full_summary": summ, "session": sn.model_dump() if sn else {}}


def build_student_pack(sid: str, lang: str) -> dict:
    """Produce study materials."""
    store = SnapBackStorage()
    bundle = store.fetch_bundle_or_raise(sid)
    txt = "\n".join(c.text for c in bundle.transcript)
    pack = _boot_engine().generate_study_pack(txt, lang)
    return {"session_id": sid, "study_pack": pack.model_dump()}
