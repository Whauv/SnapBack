"""HTTP tests for the recap route."""

from __future__ import annotations

import unittest

from tests._support import (
    TOKEN_ALICE,
    BackendTestCase,
    auth_headers,
    ingest_transcript,
    start_session,
)


class RecapRouteTests(BackendTestCase):
    def _seed_session(self) -> str:
        session_id = start_session(self.client)
        ingest_transcript(
            self.client,
            session_id,
            "We are introducing gradient descent and discussing the cost function.",
            "2026-04-07T10:00:00+00:00",
        )
        ingest_transcript(
            self.client,
            session_id,
            "This will be on the exam, so remember the update rule and learning rate tradeoff.",
            "2026-04-07T10:01:00+00:00",
        )
        return session_id

    def test_recap_generates_summary_and_alerts(self):
        session_id = self._seed_session()
        response = self.client.post(
            "/recap",
            headers=auth_headers(TOKEN_ALICE),
            json={
                "session_id": session_id,
                "from_timestamp": "2026-04-07T09:59:00+00:00",
                "to_timestamp": "2026-04-07T10:02:00+00:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["summary"])
        self.assertTrue(body["missed_alerts"])

    def test_recap_rejects_inverted_window(self):
        session_id = self._seed_session()
        response = self.client.post(
            "/recap",
            headers=auth_headers(TOKEN_ALICE),
            json={
                "session_id": session_id,
                "from_timestamp": "2026-04-07T10:02:00+00:00",
                "to_timestamp": "2026-04-07T09:59:00+00:00",
            },
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
