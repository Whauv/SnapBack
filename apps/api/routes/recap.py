"""Recap generation routes."""

from fastapi import Request

from apps.api.dependencies import get_request_principal, session_service
from apps.api.routes._compat import APIRouter
from services.api.contracts import RecapRequest

router = APIRouter(tags=["recap"])


@router.post("/recap")
def generate_recap(payload: RecapRequest, request: Request) -> dict:
    """Generate a recap for a specific time window within a session."""
    principal = get_request_principal(request)
    return session_service.generate_recap(
        principal=principal,
        session_id=payload.session_id,
        from_timestamp=payload.from_timestamp,
        to_timestamp=payload.to_timestamp,
    )
