"""App-level and security tests for the SnapBack API.

These run against the real FastAPI application via ``TestClient`` (no framework
stubs), so they exercise actual routing, request validation, and the full
middleware stack: trusted-host, CORS, auth, rate limiting, telemetry, and
security headers.
"""

from __future__ import annotations

import importlib
import os
import unittest

from tests._support import BackendTestCase, auth_headers


class AppSecurityTests(BackendTestCase):
    def test_root_redirects_to_docs(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/docs")

    def test_health_is_public_and_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_missing_token_is_rejected(self):
        response = self.client.post("/session/start", json={"mode": "cloud"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Missing API token.")

    def test_invalid_token_is_rejected(self):
        response = self.client.post(
            "/session/start",
            headers=auth_headers("not-a-real-token"),
            json={"mode": "cloud"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid API token.")

    def test_x_snapback_token_header_is_accepted(self):
        response = self.client.post(
            "/session/start",
            headers={"X-SnapBack-Token": "token-alice"},
            json={"mode": "cloud", "language": "English", "recap_length": "standard"},
        )
        self.assertEqual(response.status_code, 200)

    def test_security_headers_present_on_success(self):
        response = self.client.get("/health")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("X-Request-ID", response.headers)

    def test_security_headers_present_on_auth_failure(self):
        response = self.client.post("/session/start", json={"mode": "cloud"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("Content-Security-Policy", response.headers)

    def test_invalid_payload_returns_422(self):
        response = self.client.post(
            "/session/start",
            headers=auth_headers("token-alice"),
            json={"mode": "telepathy"},
        )
        self.assertEqual(response.status_code, 422)


class RateLimitTests(BackendTestCase):
    # The settings layer clamps the request limit to a minimum of 10.
    ENV_OVERRIDES = {"RATE_LIMIT_REQUESTS": "10", "RATE_LIMIT_WINDOW_SECONDS": "60"}

    def test_rate_limit_returns_429_after_limit(self):
        headers = auth_headers("token-alice")
        payload = {"mode": "cloud", "language": "English", "recap_length": "standard"}
        statuses = [
            self.client.post("/session/start", headers=headers, json=payload).status_code
            for _ in range(11)
        ]
        self.assertTrue(all(status == 200 for status in statuses[:10]), statuses)
        self.assertEqual(statuses[10], 429)


class SettingsAndContractUnitTests(unittest.TestCase):
    """Pure unit tests that do not need the app wired up."""

    def test_production_settings_require_explicit_tokens(self):
        saved = {key: os.environ.get(key) for key in ("APP_ENV", "SNAPBACK_API_TOKENS")}
        os.environ["APP_ENV"] = "production"
        os.environ["SNAPBACK_API_TOKENS"] = ""
        try:
            settings_module = importlib.reload(importlib.import_module("services.api.settings"))
            with self.assertRaises(RuntimeError):
                settings_module.AppSettings.from_env()
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            importlib.reload(importlib.import_module("services.api.settings"))

    def test_contract_timestamp_validation(self):
        contracts = importlib.import_module("services.api.contracts")
        with self.assertRaises(ValueError) as context:
            contracts.parse_timestamp("not-a-timestamp")
        self.assertIn("Timestamps must be valid ISO-8601 strings", str(context.exception))

    def test_contract_timestamp_normalizes_to_utc(self):
        contracts = importlib.import_module("services.api.contracts")
        # Zulu and explicit +00:00 both canonicalize to +00:00.
        self.assertEqual(contracts.parse_timestamp("2026-04-07T10:00:00Z"), "2026-04-07T10:00:00+00:00")
        self.assertEqual(
            contracts.parse_timestamp("2026-04-07T10:00:00+00:00"),
            "2026-04-07T10:00:00+00:00",
        )
        # A non-UTC offset is converted to the equivalent UTC instant.
        self.assertEqual(
            contracts.parse_timestamp("2026-04-07T15:00:00+05:00"),
            "2026-04-07T10:00:00+00:00",
        )
        # A naive timestamp is assumed to be UTC.
        self.assertEqual(
            contracts.parse_timestamp("2026-04-07T10:00:00"),
            "2026-04-07T10:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
