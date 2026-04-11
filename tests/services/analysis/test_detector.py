import unittest

from services.analysis.detector import detect_missed_alerts, detect_topic_shift


class DetectorTests(unittest.TestCase):
    def test_detect_topic_shift_flags_clear_change(self):
        previous = "Today we are solving linear algebra matrix equations and eigenvalue proofs."
        current = "Now we are switching to cellular respiration and ATP production in biology."
        self.assertTrue(detect_topic_shift(previous, current))

    def test_detect_topic_shift_ignores_empty_or_same_text(self):
        self.assertFalse(detect_topic_shift("", "Some text"))
        self.assertFalse(detect_topic_shift("Repeated concept", "Repeated concept"))

    def test_detect_missed_alerts_returns_matching_chunks(self):
        alerts = detect_missed_alerts(
            [
                {"text": "This will be on the exam, so write it down.", "timestamp": "2026-01-01T00:00:00+00:00"},
                {"text": "Regular explanation without signal phrase.", "timestamp": "2026-01-01T00:01:00+00:00"},
            ]
        )
        self.assertEqual(
            alerts,
            [
                {
                    "text": "This will be on the exam, so write it down.",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
