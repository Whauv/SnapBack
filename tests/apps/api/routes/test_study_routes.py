"""HTTP tests for the study-pack route."""

from __future__ import annotations

import unittest

from tests._support import (
    TOKEN_ALICE,
    BackendTestCase,
    auth_headers,
    ingest_transcript,
    start_session,
)


class StudyRouteTests(BackendTestCase):
    def test_study_pack_contains_flashcards(self):
        session_id = start_session(self.client)
        ingest_transcript(
            self.client,
            session_id,
            "Gradient descent optimizes the cost function using the learning rate.",
            "2026-04-07T10:00:00+00:00",
        )
        response = self.client.post(
            "/study/pack",
            headers=auth_headers(TOKEN_ALICE),
            json={"session_id": session_id},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["session_id"], session_id)
        self.assertTrue(body["study_pack"]["flashcards"])


if __name__ == "__main__":
    unittest.main()
