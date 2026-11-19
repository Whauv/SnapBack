"""Service-layer tests for SessionService edge cases.

Some guards (transcript size, audio size) are enforced in the service but are
not reachable through the HTTP route because the route pre-truncates input, so
they are verified here directly against the reloaded service instance.
"""

from __future__ import annotations

import base64
import unittest

from fastapi import HTTPException

from tests._support import BackendTestCase

TS = "2026-04-07T10:00:00+00:00"


class SessionServiceGuardTests(BackendTestCase):
    def setUp(self):
        super().setUp()
        deps = self.ctx.modules["apps.api.dependencies"]
        auth = self.ctx.modules["services.api.auth"]
        self.service = deps.session_service
        self.alice = auth.AuthenticatedPrincipal(principal_id="principal:alice", token_name="alice")
        self.bob = auth.AuthenticatedPrincipal(principal_id="principal:bob", token_name="bob")
        self.session_id = self.service.start_session(
            principal=self.alice, mode="cloud", language="English", recap_length="standard"
        )["session_id"]

    def test_transcript_size_limit(self):
        oversized = "a" * (self.service.settings.max_transcript_chars + 1)
        with self.assertRaises(HTTPException) as ctx:
            self.service.ingest_transcript(
                principal=self.alice, session_id=self.session_id, text=oversized, timestamp=TS
            )
        self.assertEqual(ctx.exception.status_code, 413)

    def test_unsupported_audio_mime(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service.ingest_audio_chunk(
                principal=self.alice,
                session_id=self.session_id,
                chunk_index=0,
                mime_type="audio/aiff",
                audio_base64=base64.b64encode(b"x").decode("ascii"),
                timestamp=TS,
                source="test",
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_empty_audio_payload(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service.ingest_audio_chunk(
                principal=self.alice,
                session_id=self.session_id,
                chunk_index=0,
                mime_type="audio/webm",
                audio_base64=base64.b64encode(b"").decode("ascii"),
                timestamp=TS,
                source="test",
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_oversized_audio_payload(self):
        big = b"x" * (self.service.settings.max_audio_chunk_bytes + 1)
        with self.assertRaises(HTTPException) as ctx:
            self.service.ingest_audio_chunk(
                principal=self.alice,
                session_id=self.session_id,
                chunk_index=0,
                mime_type="audio/webm",
                audio_base64=base64.b64encode(big).decode("ascii"),
                timestamp=TS,
                source="test",
            )
        self.assertEqual(ctx.exception.status_code, 413)

    def test_cross_principal_access_is_blocked(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_session_transcript(principal=self.bob, session_id=self.session_id)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
