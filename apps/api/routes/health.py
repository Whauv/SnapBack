"""Health and root routes."""

from fastapi.responses import RedirectResponse

from apps.api.dependencies import settings
from apps.api.routes._compat import APIRouter

router = APIRouter()


@router.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    """Redirect to docs or health depending on API docs availability."""
    return RedirectResponse(url="/docs" if settings.allow_docs else "/health")


@router.get("/health")
def health_check() -> dict[str, str]:
    """Check the health of the API."""
    return {"status": "ok"}
