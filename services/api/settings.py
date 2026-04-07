"""Application settings and environment parsing for the SnapBack API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DEV_API_TOKEN = "snapback-local-dev-token"


def parse_csv(raw_value: str, fallback: list[str]) -> list[str]:
    values = [value.strip() for value in raw_value.split(",") if value.strip()]
    return values or fallback


def parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def parse_token_map(raw_value: str, *, allow_dev_default: bool) -> dict[str, str]:
    token_map: dict[str, str] = {}
    for item in [segment.strip() for segment in raw_value.split(",") if segment.strip()]:
        if ":" not in item:
            continue
        label, token = item.split(":", 1)
        label = label.strip()
        token = token.strip()
        if label and token:
            token_map[token] = label
    if token_map or not allow_dev_default:
        return token_map
    return {DEFAULT_DEV_API_TOKEN: "local-dev"}


@dataclass(frozen=True)
class AppSettings:
    app_env: str
    auto_delete_after_hours: int
    notion_api_key: str
    groq_api_key: str | None
    cors_origins: list[str]
    trusted_hosts: list[str]
    api_tokens: dict[str, str]
    allow_docs: bool
    log_level: str
    rate_limit_requests: int
    rate_limit_window_seconds: int
    max_transcript_chars: int
    max_audio_chunk_bytes: int

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @classmethod
    def from_env(cls) -> "AppSettings":
        app_env = os.getenv("APP_ENV", "development").strip().lower()
        allow_dev_default = app_env != "production"
        api_tokens = parse_token_map(
            os.getenv("SNAPBACK_API_TOKENS", ""),
            allow_dev_default=allow_dev_default,
        )
        if app_env == "production" and not api_tokens:
            raise RuntimeError("SNAPBACK_API_TOKENS must be configured in production.")

        return cls(
            app_env=app_env,
            auto_delete_after_hours=max(1, int(os.getenv("AUTO_DELETE_AFTER_HOURS", "24"))),
            notion_api_key=os.getenv("NOTION_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            cors_origins=parse_csv(
                os.getenv("CORS_ALLOW_ORIGINS", ""),
                ["http://localhost:5173", "http://127.0.0.1:5173"],
            ),
            trusted_hosts=parse_csv(
                os.getenv("TRUSTED_HOSTS", ""),
                ["localhost", "127.0.0.1", "*.ngrok-free.app"],
            ),
            api_tokens=api_tokens,
            allow_docs=parse_bool(os.getenv("ENABLE_API_DOCS"), default=app_env != "production"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            rate_limit_requests=max(10, int(os.getenv("RATE_LIMIT_REQUESTS", "120"))),
            rate_limit_window_seconds=max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))),
            max_transcript_chars=max(256, int(os.getenv("MAX_TRANSCRIPT_CHARS", "8000"))),
            max_audio_chunk_bytes=max(1024, int(os.getenv("MAX_AUDIO_CHUNK_BYTES", str(5 * 1024 * 1024)))),
        )
