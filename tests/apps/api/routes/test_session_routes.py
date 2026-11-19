"""HTTP tests for the session lifecycle routes."""

from __future__ import annotations

import base64
import unittest

from tests._support import (
    TOKEN_ALICE,
    TOKEN_BOB,
    BackendTestCase,
    auth_headers,
    ingest_transcript,
    start_session,
)

TS = "2026-04-07T10:00:00+00:00"


class SessionRouteTests(BackendTestCase):
    def test_start_session_returns_identifiers(self):
        response = self.client.post(
            "/session/start",
            headers=auth_headers(TOKEN_ALICE),
            json={"mode": "cloud", "language": "English", "recap_length": "standard"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("session_id", body)
        self.assertIn("start_timestamp", body)

    def test_transcript_roundtrip(self):
        session_id = start_session(self.client)
        ingest_transcript(self.client, session_id, "Gradient descent and the cost function.", TS)

        response = self.client.get(
            f"/session/{session_id}/transcript",
            headers=auth_headers(TOKEN_ALICE),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["transcript"]), 1)
        self.assertIn("Gradient descent", body["transcript"][0]["text"])

    def test_owner_scope_isolation(self):
        session_id = start_session(self.client, TOKEN_ALICE)
        response = self.client.get(
            f"/session/{session_id}/transcript",
            headers=auth_headers(TOKEN_BOB),
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_session_returns_404(self):
        response = self.client.get(
            "/session/does-not-exist/transcript",
            headers=auth_headers(TOKEN_ALICE),
        )
        self.assertEqual(response.status_code, 404)

    def test_audio_chunk_valid_payload(self):
        session_id = start_session(self.client)
        audio_b64 = base64.b64encode(b"fake-audio-bytes").decode("ascii")
        response = self.client.post(
            "/session/audio-chunk",
            headers=auth_headers(TOKEN_ALICE),
            json={
                "session_id": session_id,
                "chunk_index": 0,
                "mime_type": "audio/webm",
                "audio_base64": audio_b64,
                "timestamp": TS,
                "source": "chrome-extension",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("audio_chunk", response.json())

    def test_audio_chunk_invalid_base64_is_rejected(self):
        session_id = start_session(self.client)
        response = self.client.post(
            "/session/audio-chunk",
            headers=auth_headers(TOKEN_ALICE),
            json={
                "session_id": session_id,
                "chunk_index": 0,
                "mime_type": "audio/webm",
                "audio_base64": "%%%not-valid-base64%%%",
                "timestamp": TS,
                "source": "chrome-extension",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_timestamps_are_normalized_to_utc(self):
        session_id = start_session(self.client)
        # Sent later-in-the-day but with a +05:00 offset -> 10:00Z, i.e. earlier.
        ingest_transcript(self.client, session_id, "offset chunk", "2026-04-07T15:00:00+05:00")
        ingest_transcript(self.client, session_id, "zulu chunk", "2026-04-07T10:30:00Z")
        response = self.client.get(
            f"/session/{session_id}/transcript",
            headers=auth_headers(TOKEN_ALICE),
        )
        transcript = response.json()["transcript"]
        self.assertEqual([c["text"] for c in transcript], ["offset chunk", "zulu chunk"])
        self.assertEqual(transcript[0]["timestamp"], "2026-04-07T10:00:00+00:00")
        self.assertEqual(transcript[1]["timestamp"], "2026-04-07T10:30:00+00:00")

    def test_complete_session_returns_full_summary(self):
        session_id = start_session(self.client)
        ingest_transcript(self.client, session_id, "We covered gradient descent today.", TS)
        response = self.client.post(
            "/session/end",
            headers=auth_headers(TOKEN_ALICE),
            json={"session_id": session_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["full_summary"])


if __name__ == "__main__":
    unittest.main()
