"""Study pack routes."""

from fastapi import Request

from apps.api.dependencies import get_request_principal, session_service
from apps.api.routes._compat import APIRouter
from services.api.contracts import StudyPackRequest

router = APIRouter(tags=["study"])


@router.post("/study/pack")
def generate_study_pack(payload: StudyPackRequest, request: Request) -> dict:
    """Generate a study pack for a session."""
    principal = get_request_principal(request)
    return session_service.generate_study_pack(principal=principal, session_id=payload.session_id)
