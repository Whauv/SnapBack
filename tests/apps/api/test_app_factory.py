"""Tests for the FastAPI app factory wiring."""

from __future__ import annotations

import unittest

from tests._support import BackendTestCase


class AppFactoryTests(BackendTestCase):
    def test_expected_routes_are_registered(self):
        paths = {getattr(route, "path", None) for route in self.ctx.app.routes}
        for expected in (
            "/",
            "/health",
            "/session/start",
            "/session/transcript",
            "/session/audio-chunk",
            "/session/{session_id}/transcript",
            "/session/end",
            "/recap",
            "/study/pack",
            "/export/pdf",
            "/export/markdown",
            "/export/notion",
        ):
            self.assertIn(expected, paths)

    def test_docs_enabled_in_development(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["title"], "SnapBack API")


if __name__ == "__main__":
    unittest.main()
