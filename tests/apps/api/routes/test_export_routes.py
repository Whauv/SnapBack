"""HTTP tests for the export routes."""

from __future__ import annotations

import unittest

from tests._support import (
    TOKEN_ALICE,
    BackendTestCase,
    auth_headers,
    ingest_transcript,
    start_session,
)


class ExportRouteTests(BackendTestCase):
    def _seed(self) -> str:
        session_id = start_session(self.client)
        ingest_transcript(
            self.client,
            session_id,
            "Gradient descent and the cost function were introduced.",
            "2026-04-07T10:00:00+00:00",
        )
        return session_id

    def test_export_markdown(self):
        session_id = self._seed()
        response = self.client.post(
            "/export/markdown",
            headers=auth_headers(TOKEN_ALICE),
            json={"session_id": session_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response.headers["content-type"])
        self.assertIn(session_id, response.text)
        self.assertIn("## Transcript", response.text)

    def test_export_pdf(self):
        session_id = self._seed()
        response = self.client.post(
            "/export/pdf",
            headers=auth_headers(TOKEN_ALICE),
            json={"session_id": session_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_export_notion_requires_api_key(self):
        session_id = self._seed()
        response = self.client.post(
            "/export/notion",
            headers=auth_headers(TOKEN_ALICE),
            json={"session_id": session_id, "page_id": "page-123"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Notion API key", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
