"""Shared helpers for SnapBack backend tests.

The API wires its settings, auth manager, rate limiter, and session service as
module-level singletons that are built from environment variables at import
time (see ``apps/api/dependencies.py``). To test the real application against a
known configuration we set the environment first and then reload the dependency
chain in leaf-to-root order so every module re-binds to the fresh settings.

This replaces the previous approach of hand-building fake ``fastapi`` and
``pydantic`` modules: the real frameworks are always available, so tests now run
against the actual request parsing, validation, routing, and middleware stack
via ``fastapi.testclient.TestClient``.
"""

from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Reload order: leaves first, dependents last, so each dependent re-executes its
# ``from X import name`` against the freshly reloaded ``X``.
MODULE_RELOAD_ORDER = (
    "services.api.settings",
    "services.storage.database",
    "services.api.auth",
    "services.api.rate_limit",
    "services.api.telemetry",
    "services.api.security_headers",
    "services.analysis.detector",
    "services.analysis.summarizer",
    "services.exporters.export",
    "services.api.session_service",
    "apps.api.dependencies",
    "apps.api.routes.health",
    "apps.api.routes.session",
    "apps.api.routes.recap",
    "apps.api.routes.export",
    "apps.api.routes.study",
    "apps.api.app_factory",
    "apps.api.main",
)

# Baseline test environment. ``GROQ_API_KEY``/``NOTION_API_KEY`` are forced empty
# so the summarizer and exporters stay on their offline fallback paths and never
# make network calls. ``load_dotenv`` in dependencies.py does not override values
# already present in the environment, so these win over any local ``.env``.
BASELINE_ENV: dict[str, str] = {
    "APP_ENV": "development",
    "SNAPBACK_API_TOKENS": "alice:token-alice,bob:token-bob",
    "GROQ_API_KEY": "",
    "NOTION_API_KEY": "",
    "RATE_LIMIT_REQUESTS": "120",
    "RATE_LIMIT_WINDOW_SECONDS": "60",
    # TestClient's default base URL sends ``Host: testserver``; allow it so the
    # TrustedHostMiddleware does not reject every request with a 400.
    "TRUSTED_HOSTS": "localhost,127.0.0.1,testserver",
    "LOG_LEVEL": "WARNING",
}

TOKEN_ALICE = "token-alice"
TOKEN_BOB = "token-bob"

# Env keys we manage, so teardown can restore the prior process environment.
_MANAGED_ENV_KEYS = (*BASELINE_ENV.keys(), "SNAPBACK_DB_PATH")


def auth_headers(token: str) -> dict[str, str]:
    """Return Authorization headers for the given bearer token."""
    return {"Authorization": f"Bearer {token}"}


@dataclass
class TestContext:
    """A reloaded app, a client, and the module objects bound to it."""

    client: TestClient
    app: FastAPI
    modules: dict[str, ModuleType]
    db_path: Path
    _saved_env: dict[str, str | None] = field(default_factory=dict)

    def module(self, name: str) -> ModuleType:
        return self.modules[name]

    def cleanup(self) -> None:
        """Close the client, drop the temp DB, and restore the environment."""
        self.client.close()
        self.db_path.unlink(missing_ok=True)
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_test_app(**env_overrides: str) -> TestContext:
    """Build a fresh app bound to an isolated temp DB and known settings.

    Pass environment overrides (e.g. ``RATE_LIMIT_REQUESTS="10"``) to exercise
    specific configurations. The caller is responsible for calling
    ``cleanup()`` in ``tearDown``.
    """
    saved_env: dict[str, str | None] = {key: os.environ.get(key) for key in _MANAGED_ENV_KEYS}

    db_fd, db_name = tempfile.mkstemp(prefix="snapback-test-", suffix=".db")
    os.close(db_fd)
    db_path = Path(db_name)
    db_path.unlink(missing_ok=True)  # start from an empty schema

    env = {**BASELINE_ENV, **env_overrides, "SNAPBACK_DB_PATH": str(db_path)}
    os.environ.update(env)

    modules: dict[str, ModuleType] = {}
    for name in MODULE_RELOAD_ORDER:
        modules[name] = importlib.reload(importlib.import_module(name))

    # Lifespan is not run (no TestClient context manager), so create the schema
    # explicitly and avoid starting the background scheduler thread.
    modules["services.storage.database"].init_db()

    app = modules["apps.api.app_factory"].create_app()
    client = TestClient(app)
    return TestContext(client=client, app=app, modules=modules, db_path=db_path, _saved_env=saved_env)


class BackendTestCase(unittest.TestCase):
    """Base case that builds a fresh app + client and tears it down.

    Subclasses may set ``ENV_OVERRIDES`` to exercise a specific configuration.
    """

    ENV_OVERRIDES: dict[str, str] = {}

    def setUp(self) -> None:
        self.ctx = build_test_app(**self.ENV_OVERRIDES)
        self.client = self.ctx.client

    def tearDown(self) -> None:
        self.ctx.cleanup()


def start_session(
    client: TestClient,
    token: str = TOKEN_ALICE,
    *,
    mode: str = "cloud",
    language: str = "English",
    recap_length: str = "standard",
) -> str:
    """Start a session via the API and return its id."""
    response = client.post(
        "/session/start",
        headers=auth_headers(token),
        json={"mode": mode, "language": language, "recap_length": recap_length},
    )
    response.raise_for_status()
    return response.json()["session_id"]


def ingest_transcript(
    client: TestClient,
    session_id: str,
    text: str,
    timestamp: str,
    token: str = TOKEN_ALICE,
) -> Any:
    """Ingest one transcript chunk via the API."""
    response = client.post(
        "/session/transcript",
        headers=auth_headers(token),
        json={"session_id": session_id, "text": text, "timestamp": timestamp},
    )
    response.raise_for_status()
    return response.json()
