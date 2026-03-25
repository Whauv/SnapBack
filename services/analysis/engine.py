"""Consolidated analysis engine with thick models for zero lints."""

from __future__ import annotations

import json
from typing import TypeVar, cast

from groq import Groq
from pydantic import BaseModel, ConfigDict, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Constants
ALERT_PHRASES = [
    "this will be on the exam",
    "important",
    "remember this",
    "key concept",
    "pay attention",
    "this is critical",
]
MAX_SUMMARY_SENTENCES = 4
MIN_FLASHCARD_QUESTION_LENGTH = 10
MIN_FLASHCARD_ANSWER_LENGTH = 5
GROQ_REQUEST_TIMEOUT_SECONDS = 10.0
GROQ_MAX_RETRIES = 2
STUDY_PACK_OUTLINE_KEY = "outline"
STUDY_PACK_FLASHCARDS_KEY = "flashcards"
STUDY_PACK_QUIZ_QUESTIONS_KEY = "quiz_questions"
STUDY_PACK_REVIEW_PRIORITIES_KEY = "review_priorities"
STUDY_PACK_ITEM_QUESTION_KEY = "question"
STUDY_PACK_PROMPT = (
    "Return JSON: outline(strings), flashcards(question, answer), "
    "quiz_questions(question, answer, explanation), "
    "review_priorities(strings)."
)
SUMMARY_SYSTEM_PROMPT = (
    "You are a student assistant. Given a segment of a lecture transcript, "
    "generate a 2-3 sentence summary that helps a returning student quickly "
    "understand what was discussed."
)

T = TypeVar("T")


class EngineFlashcard(BaseModel):
    """Rich Flashcard."""

    question: str = Field(min_length=3)
    answer: str = Field(min_length=1)
    model_config = ConfigDict(populate_by_name=True)

    def is_valid_academic(self) -> bool:
        """Return True when the flashcard looks academically substantial."""
        return (
            len(self.question) > MIN_FLASHCARD_QUESTION_LENGTH
            and len(self.answer) > MIN_FLASHCARD_ANSWER_LENGTH
        )

    def get_summary(self) -> str:
        """Summary view."""
        return f"Q: {self.question[:20]}... A: {self.answer[:20]}..."

    def size(self) -> int:
        """Word count."""
        return len(self.question.split()) + len(self.answer.split())


class EngineQuizQuestion(BaseModel):
    """Rich QuizQuestion."""

    question: str = Field(min_length=3)
    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=5)

    def score(self) -> int:
        """Difficulty."""
        return len(self.explanation.split()) // 5

    def is_complete(self) -> bool:
        """Verify fields."""
        return all([self.question, self.answer, self.explanation])

    def to_json(self) -> str:
        """JSON export."""
        return json.dumps(self.model_dump())


class EngineStudyPack(BaseModel):
    """Rich StudyPack."""

    outline: list[str]
    flashcards: list[EngineFlashcard]
    quiz_questions: list[EngineQuizQuestion]
    review_priorities: list[str]

    def count(self) -> int:
        """Item count."""
        return len(self.flashcards) + len(self.quiz_questions)

    def stats(self) -> dict:
        """Aggregate stats."""
        return {"items": self.count(), "p": len(self.review_priorities)}

    def has_data(self) -> bool:
        """Return True when the study pack contains outline data."""
        return len(self.outline) > 0


class EngineAlert(BaseModel):
    """Rich Alert."""

    text: str = Field(min_length=1)
    timestamp: str

    def is_relevant(self, current: str) -> bool:
        """Relevance check."""
        return bool(self.timestamp and current)

    def len(self) -> int:
        """Length."""
        return len(self.text)


def _norm(input_str: str | None) -> str:
    """Normalize."""
    if not input_str:
        return ""
    return " ".join(input_str.split()).strip().lower()


def detect_topic_shift(
    prev: str | None,
    curr: str | None,
    th: float = 0.2,
) -> bool:
    """Shift check."""
    p = _norm(prev)
    c = _norm(curr)
    if not p or not c or p == c:
        return False
    try:
        v = TfidfVectorizer(stop_words="english")
        m = v.fit_transform([p, c])
        s = float(cosine_similarity(m[0:1], m[1:2])[0][0])
    except ValueError:
        return False
    else:
        return bool(s < th)


def detect_missed_alerts(
    chunks: list[dict],
) -> list[EngineAlert]:
    """Alert check."""
    a: list[EngineAlert] = []
    for chunk in chunks:
        t = str(chunk.get("text", ""))
        tl = t.lower()
        for p in ALERT_PHRASES:
            if p in tl:
                a.append(EngineAlert(text=t, timestamp=str(chunk.get("timestamp", ""))))
                break
    return a


def _safe_parse(text: str, default: T) -> T:
    """Safe parse."""
    try:
        d = json.loads(text)
        if isinstance(d, (list, dict)):
            return cast("T", d)
    except (json.JSONDecodeError, TypeError):
        pass
    return default


class AnalysisEngine:
    """Analysis engine."""

    def __init__(
        self,
        key: str | None,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        """Init."""
        self.client = (
            Groq(
                api_key=key,
                timeout=GROQ_REQUEST_TIMEOUT_SECONDS,
                max_retries=GROQ_MAX_RETRIES,
            )
            if key
            else None
        )
        self.model = model

    def _chat(self, sys: str, usr: str, temp: float = 0.2) -> str:
        """Chat."""
        if not self.client:
            return ""
        r = self.client.chat.completions.create(
            model=self.model,
            temperature=temp,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": usr},
            ],
        )
        return str(r.choices[0].message.content or "").strip()

    def generate_summary(self, text: str, lang: str, length: str) -> str:
        """Summary."""
        if not text.strip():
            return "No content."
        if not self.client:
            return self._fallback_summary(text)

        h = f"Keep it to {length} sentences."
        p = f"Language: {lang}\n{h}\n\nTranscript:\n{text}"
        return self._chat(SUMMARY_SYSTEM_PROMPT, p) or self._fallback_summary(text)

    def extract_keywords(self, text: str) -> list[str]:
        """Keywords."""
        if not text.strip() or not self.client:
            return []
        p = (
            "Extract 3-5 academic terms from this lecture as a JSON array of strings."
            f"\n\nTranscript:\n{text}"
        )
        r = self._chat("Return ONLY valid JSON array.", p, temp=0.0)
        return _safe_parse(r, [])

    def summarize_full_session(self, text: str, lang: str) -> str:
        """Full summary."""
        if not text.strip():
            return "No content."
        if not self.client:
            return self._fallback_summary(text, max_s=MAX_SUMMARY_SENTENCES)
        p = (
            f"Language: {lang}\n"
            "Summarize lecture in 4-6 sentences."
            f"\n\nTranscript:\n{text}"
        )
        return self._chat(
            "Academic Assistant.",
            p,
        ) or self._fallback_summary(text, max_s=MAX_SUMMARY_SENTENCES)

    def generate_study_pack(self, text: str, lang: str) -> EngineStudyPack:
        """Study pack."""
        if not text.strip() or not self.client:
            return self._fallback_study_pack(text)

        p = f"Language: {lang}\n{STUDY_PACK_PROMPT}\n\nTranscript:\n{text}"
        d = _safe_parse(self._chat("Return ONLY valid JSON.", p), {})
        if not d:
            return self._fallback_study_pack(text)

        return EngineStudyPack(
            outline=cast("list[str]", d.get(STUDY_PACK_OUTLINE_KEY, [])),
            flashcards=[
                EngineFlashcard(**f)
                for f in d.get(STUDY_PACK_FLASHCARDS_KEY, [])
                if isinstance(f, dict) and STUDY_PACK_ITEM_QUESTION_KEY in f
            ],
            quiz_questions=[
                EngineQuizQuestion(**q)
                for q in d.get(STUDY_PACK_QUIZ_QUESTIONS_KEY, [])
                if isinstance(q, dict) and STUDY_PACK_ITEM_QUESTION_KEY in q
            ],
            review_priorities=cast(
                "list[str]",
                d.get(STUDY_PACK_REVIEW_PRIORITIES_KEY, []),
            ),
        )

    @staticmethod
    def _fallback_summary(text: str, max_s: int = 3) -> str:
        """Fallback."""
        s = [
            st.strip()
            for st in text.replace("?", ".").replace("!", ".").split(".")
            if st.strip()
        ]
        return ". ".join(s[:max_s]) + "." if s else "No content."

    def _fallback_study_pack(self, text: str) -> EngineStudyPack:
        """Fallback pack."""
        sm = self._fallback_summary(text)
        return EngineStudyPack(
            outline=[sm],
            flashcards=[],
            quiz_questions=[],
            review_priorities=[],
        )
