"""Summarization and study pack generation using Groq API."""

from __future__ import annotations

import json
from typing import Any

from groq import Groq

MIN_WORD_LENGTH = 4
MAX_SUMMARY_SENTENCES = 4

SUMMARY_SYSTEM_PROMPT = (
    "You are a student assistant. Given a segment of a lecture transcript, "
    "generate a 2-3 sentence summary that helps a returning student quickly "
    "understand what was discussed, what key concepts were introduced, and "
    "where the lecture currently is. Be concise and use academic language."
)


def _safe_json_array(text: str) -> list[str]:
    """Safely parse a JSON array of strings."""
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return []


def _safe_json_object(text: str) -> dict[str, Any]:
    """Safely parse a JSON object."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {}


class GroqSummarizer:
    """Summarizer using the Groq API for lecture recaps and study packs."""

    def __init__(
        self,
        api_key: str | None,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        """Initialize the summarizer with an API key and model."""
        self.api_key = api_key
        self.model = model
        self.client = Groq(api_key=api_key) if api_key else None

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request to Groq."""
        if not self.client:
            return ""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    def generate_summary(
        self,
        transcript_text: str,
        language: str = "English",
        recap_length: str = "standard",
    ) -> str:
        """Generate a short summary of a transcript segment."""
        if not transcript_text.strip():
            return "No transcript was captured during the requested time window."
        if not self.client:
            return self._fallback_summary(transcript_text)

        length_hint = {
            "brief": "Keep it to 2 sentences max.",
            "standard": "Keep it to 2-3 sentences.",
            "detailed": "Use 3 concise sentences if needed.",
        }.get(recap_length.lower(), "Keep it to 2-3 sentences.")

        user_prompt = (
            f"Preferred summary language: {language}\n"
            f"{length_hint}\n\n"
            f"Transcript segment:\n{transcript_text}"
        )
        summary = self._chat(SUMMARY_SYSTEM_PROMPT, user_prompt)
        return summary or self._fallback_summary(transcript_text)

    def extract_keywords(self, transcript_text: str) -> list[str]:
        """Extract key academic terms from a transcript segment."""
        if not transcript_text.strip():
            return []
        if not self.client:
            return self._fallback_keywords(transcript_text)

        prompt = (
            "Extract 3-5 key academic terms or concepts from this transcript "
            "segment as a JSON array of strings.\n\n"
            f"Transcript:\n{transcript_text}"
        )
        response = self._chat("Return only valid JSON.", prompt, temperature=0.0)
        keywords = _safe_json_array(response)
        return keywords or self._fallback_keywords(transcript_text)

    def summarize_full_session(
        self,
        transcript_text: str,
        language: str = "English",
    ) -> str:
        """Generate a comprehensive summary of the full lecture session."""
        if not transcript_text.strip():
            return "No transcript was captured for this lecture session."
        if not self.client:
            return self._fallback_summary(
                transcript_text,
                max_sentences=MAX_SUMMARY_SENTENCES,
            )
        prompt = (
            f"Preferred language: {language}\n"
            "Summarize the full lecture in 4-6 sentences. Highlight the main "
            "throughline, important concepts, and what students should review."
            "\n\nTranscript:\n{transcript_text}"
        )
        summary = self._chat(
            "You are a study assistant producing a polished lecture recap.",
            prompt,
            temperature=0.2,
        )
        return summary or self._fallback_summary(
            transcript_text,
            max_sentences=MAX_SUMMARY_SENTENCES,
        )

    def generate_study_pack(
        self,
        transcript_text: str,
        language: str = "English",
    ) -> dict[str, Any]:
        """Generate a study pack (outline, flashcards, quiz) from transcript."""
        if not transcript_text.strip():
            return self._fallback_study_pack(transcript_text)
        if not self.client:
            return self._fallback_study_pack(transcript_text)

        prompt = (
            f"Preferred language: {language}\n"
            "Return valid JSON with these keys only: "
            "`outline` (array of 3-5 short strings), "
            "`flashcards` (array of objects with `question` and `answer`), "
            "`quiz_questions` (array of objects with `question`, `answer`, "
            "and `explanation`), "
            "`review_priorities` (array of 3 short strings). "
            "Use concise academic phrasing and make the outputs suitable "
            "for student revision.\n\n"
            f"Transcript:\n{transcript_text}"
        )
        response = self._chat(
            "You are a study assistant. Return only valid JSON.",
            prompt,
            temperature=0.2,
        )
        parsed = _safe_json_object(response)
        if not parsed:
            return self._fallback_study_pack(transcript_text)
        return {
            "outline": [
                str(item).strip()
                for item in parsed.get("outline", [])
                if str(item).strip()
            ],
            "flashcards": [
                {
                    "question": str(item.get("question", "")).strip(),
                    "answer": str(item.get("answer", "")).strip(),
                }
                for item in parsed.get("flashcards", [])
                if (
                    str(item.get("question", "")).strip()
                    and str(item.get("answer", "")).strip()
                )
            ],
            "quiz_questions": [
                {
                    "question": str(item.get("question", "")).strip(),
                    "answer": str(item.get("answer", "")).strip(),
                    "explanation": str(item.get("explanation", "")).strip(),
                }
                for item in parsed.get("quiz_questions", [])
                if (
                    str(item.get("question", "")).strip()
                    and str(item.get("answer", "")).strip()
                )
            ],
            "review_priorities": [
                str(item).strip()
                for item in parsed.get("review_priorities", [])
                if str(item).strip()
            ],
        }

    @staticmethod
    def _fallback_summary(transcript_text: str, max_sentences: int = 3) -> str:
        """Provide a simple sentence-extraction based summary fallback."""
        cleaned = " ".join(transcript_text.split())
        if not cleaned:
            return "No transcript was captured during the requested time window."
        sentences = [
            segment.strip()
            for segment in cleaned.replace("?", ".").replace("!", ".").split(".")
            if segment.strip()
        ]
        preview = ". ".join(sentences[:max_sentences]).strip()
        return f"{preview}." if preview and not preview.endswith(".") else preview

    @staticmethod
    def _fallback_keywords(transcript_text: str) -> list[str]:
        """Identify potential keywords based on word frequency."""
        words = [
            token.strip(".,!?():;[]{}\"'").lower() for token in transcript_text.split()
        ]
        stop_words = {
            "the",
            "and",
            "for",
            "that",
            "with",
            "this",
            "have",
            "from",
            "were",
            "what",
            "when",
            "where",
            "into",
            "your",
            "about",
            "they",
            "them",
            "been",
            "then",
            "than",
            "will",
            "would",
            "could",
            "should",
            "there",
            "their",
            "lecture",
            "because",
            "which",
            "while",
            "after",
            "before",
        }
        frequency: dict[str, int] = {}
        for word in words:
            if len(word) < MIN_WORD_LENGTH or word in stop_words:
                continue
            frequency[word] = frequency.get(word, 0) + 1
        ranked = sorted(frequency.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ranked[:5]]

    def _fallback_study_pack(self, transcript_text: str) -> dict[str, Any]:
        """Generate a basic study pack based on term frequency and summary."""
        summary = self._fallback_summary(
            transcript_text,
            max_sentences=MAX_SUMMARY_SENTENCES,
        )
        keywords = self._fallback_keywords(transcript_text)
        outline = [
            f"Review concept: {keyword.title()}" for keyword in keywords[:4]
        ] or [summary]
        flashcards = [
            {
                "question": (f"What is the significance of {keyword} in this lecture?"),
                "answer": (
                    f"{keyword.title()} was identified as a recurring concept "
                    f"in the session transcript."
                ),
            }
            for keyword in keywords[:4]
        ]
        quiz_questions = [
            {
                "question": f"Explain {keyword} in the context of this lecture.",
                "answer": (
                    f"{keyword.title()} appears to be one of the important "
                    f"recurring ideas discussed."
                ),
                "explanation": (
                    "This fallback prompt is based on transcript term "
                    "frequency rather than model reasoning."
                ),
            }
            for keyword in keywords[:3]
        ]
        review_priorities = [keyword.title() for keyword in keywords[:3]] or [
            "Review the lecture summary carefully."
        ]
        return {
            "outline": outline[:5],
            "flashcards": flashcards,
            "quiz_questions": quiz_questions,
            "review_priorities": review_priorities,
        }
