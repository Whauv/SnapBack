"""Compatibility helpers for FastAPI route modules."""

from __future__ import annotations

try:
    from fastapi import APIRouter
except Exception:  # pragma: no cover - used by lightweight import stubs in tests
    class APIRouter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            return None

        def get(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def post(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator
