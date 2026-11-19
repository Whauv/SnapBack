"""Tests for the telemetry middleware."""

from __future__ import annotations

import asyncio
import types
import unittest

from fastapi import Response

from services.api.telemetry import telemetry_middleware


def _request() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        state=types.SimpleNamespace(),
        method="GET",
        url=types.SimpleNamespace(path="/health"),
    )


class TelemetryMiddlewareTests(unittest.TestCase):
    def test_sets_request_id_header(self):
        async def call_next(_request):
            return Response(content=b"ok", status_code=200)

        response = asyncio.run(telemetry_middleware(_request(), call_next))
        self.assertIn("X-Request-ID", response.headers)
        self.assertTrue(response.headers["X-Request-ID"])

    def test_reraises_and_still_logs_on_error(self):
        async def call_next(_request):
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            asyncio.run(telemetry_middleware(_request(), call_next))


if __name__ == "__main__":
    unittest.main()
