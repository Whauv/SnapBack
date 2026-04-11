"""Export routes."""

from fastapi import Request
from fastapi.responses import Response

from apps.api.dependencies import get_request_principal, session_service
from apps.api.routes._compat import APIRouter
from services.api.contracts import ExportRequest, NotionExportRequest

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/pdf")
def export_pdf(payload: ExportRequest, request: Request) -> Response:
    """Export the session as a PDF document."""
    principal = get_request_principal(request)
    pdf_bytes = session_service.export_pdf(principal=principal, session_id=payload.session_id)
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/markdown")
def export_markdown(payload: ExportRequest, request: Request) -> Response:
    """Export the session as a Markdown document."""
    principal = get_request_principal(request)
    markdown = session_service.export_markdown(principal=principal, session_id=payload.session_id)
    headers = {"Content-Disposition": f'attachment; filename="snapback-{payload.session_id}.md"'}
    return Response(content=markdown, media_type="text/markdown; charset=utf-8", headers=headers)


@router.post("/notion")
def export_notion(payload: NotionExportRequest, request: Request) -> dict:
    """Export the session to a Notion page."""
    principal = get_request_principal(request)
    return session_service.export_notion(
        principal=principal,
        session_id=payload.session_id,
        page_id=payload.page_id,
        notion_api_key=payload.notion_api_key,
    )
