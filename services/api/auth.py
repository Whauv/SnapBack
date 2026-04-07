"""Authentication helpers for the SnapBack API."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from services.api.settings import AppSettings


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    principal_id: str
    token_name: str


def is_public_path(path: str) -> bool:
    return path in {"/", "/health"} or path.startswith("/docs") or path.startswith("/openapi")


class AuthManager:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def extract_token(self, request: Request) -> str | None:
        authorization = request.headers.get("authorization", "").strip()
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
            if token:
                return token
        token = request.headers.get("x-snapback-token", "").strip()
        return token or None

    def authenticate(self, request: Request) -> AuthenticatedPrincipal:
        token = self.extract_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="Missing API token.")
        token_name = self.settings.api_tokens.get(token)
        if not token_name:
            raise HTTPException(status_code=401, detail="Invalid API token.")
        return AuthenticatedPrincipal(principal_id=f"principal:{token_name}", token_name=token_name)
