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


def detect_topic_shift(previous_text: str | None, current_text: str | None, threshold: float = 0.2) -> bool:
    if not previous_text or not current_text:
        return False
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([previous_text, current_text])
    similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    return similarity < threshold


def detect_missed_alerts(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        for phrase in ALERT_PHRASES:
            if phrase in text_lower:
                alerts.append({"text": chunk["text"], "timestamp": chunk["timestamp"]})
                break
    return alerts
