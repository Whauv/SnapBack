from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ALERT_PHRASES = [
    "this will be on the exam",
    "important",
    "remember this",
    "key concept",
    "pay attention",
    "this is critical",
]


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split()).strip().lower()


def detect_topic_shift(previous_text: str | None, current_text: str | None, threshold: float = 0.2) -> bool:
    previous = _normalize_text(previous_text)
    current = _normalize_text(current_text)
    if not previous or not current or previous == current:
        return False
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([previous, current])
        similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return similarity < threshold
    except ValueError:
        return False


def detect_missed_alerts(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        for phrase in ALERT_PHRASES:
            if phrase in text_lower:
                alerts.append({"text": chunk["text"], "timestamp": chunk["timestamp"]})
                break
    return alerts
