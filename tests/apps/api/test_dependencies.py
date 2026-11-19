"""Tests for shared API dependencies and middleware helpers."""

from __future__ import annotations

import types
import unittest

from services.api.auth import is_public_path


class PublicPathTests(unittest.TestCase):
    def test_public_paths(self):
        for path in ("/", "/health", "/docs", "/docs/oauth2-redirect", "/openapi.json"):
            self.assertTrue(is_public_path(path), path)

    def test_protected_paths(self):
        for path in ("/session/start", "/recap", "/export/pdf", "/study/pack"):
            self.assertFalse(is_public_path(path), path)


class RequestPrincipalTests(unittest.TestCase):
    def test_missing_principal_raises(self):
        from apps.api.dependencies import get_request_principal

        request = types.SimpleNamespace(state=types.SimpleNamespace())
        with self.assertRaises(RuntimeError):
            get_request_principal(request)

    def test_present_principal_is_returned(self):
        from apps.api.dependencies import get_request_principal

        principal = object()
        request = types.SimpleNamespace(state=types.SimpleNamespace(principal=principal))
        self.assertIs(get_request_principal(request), principal)


if __name__ == "__main__":
    unittest.main()
