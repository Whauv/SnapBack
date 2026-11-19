import types
import unittest
from unittest import mock

from services.analysis import summarizer as summarizer_module
from services.analysis.summarizer import GroqSummarizer


def _fake_groq_returning(content: str):
    """Build a fake Groq class whose chat completion returns ``content``."""
    response = types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))]
    )
    client = mock.MagicMock()
    client.chat.completions.create.return_value = response
    return mock.MagicMock(return_value=client), client


class SummarizerTests(unittest.TestCase):
    def test_fallback_summary_handles_empty_text(self):
        summarizer = GroqSummarizer(api_key=None)
        self.assertEqual(
            summarizer.generate_summary(""),
            "No transcript was captured during the requested time window.",
        )

    def test_fallback_study_pack_returns_structured_content(self):
        summarizer = GroqSummarizer(api_key=None)
        study_pack = summarizer.generate_study_pack(
            "Gradient descent minimizes loss. The professor said this is important for the exam."
        )
        self.assertTrue(study_pack["outline"])
        self.assertTrue(study_pack["flashcards"])
        self.assertTrue(study_pack["quiz_questions"])
        self.assertTrue(study_pack["review_priorities"])

    def test_groq_summary_path_uses_client_response(self):
        fake_groq, client = _fake_groq_returning("Model-generated recap.")
        with mock.patch.object(summarizer_module, "Groq", fake_groq):
            summarizer = GroqSummarizer(api_key="test-key")
            summary = summarizer.generate_summary("Gradient descent explained.")
        self.assertEqual(summary, "Model-generated recap.")
        client.chat.completions.create.assert_called_once()

    def test_groq_failure_falls_back(self):
        fake_groq = mock.MagicMock()
        failing_client = mock.MagicMock()
        failing_client.chat.completions.create.side_effect = RuntimeError("api down")
        fake_groq.return_value = failing_client
        with mock.patch.object(summarizer_module, "Groq", fake_groq):
            summarizer = GroqSummarizer(api_key="test-key")
            summary = summarizer.generate_summary("Gradient descent explained clearly.")
        # Falls back to extractive summary rather than raising.
        self.assertIn("Gradient descent", summary)


if __name__ == "__main__":
    unittest.main()
