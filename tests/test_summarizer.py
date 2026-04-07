import unittest

from services.analysis.summarizer import GroqSummarizer


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


if __name__ == "__main__":
    unittest.main()
