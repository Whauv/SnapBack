"""Export functions using rich models and bare dict."""

from __future__ import annotations

import typing
from textwrap import fill

from fpdf import FPDF
from notion_client import Client as NotionClient

if typing.TYPE_CHECKING:
    from services.storage.database import SessionBundle


def build_markdown_export(bundle: SessionBundle) -> str:
    """Build a markdown string from the session bundle."""
    session = bundle.session
    transcript = bundle.transcript
    recaps = bundle.recaps

    lines = [
        f"# SnapBack Session {session.id}",
        "",
        f"- Started: {session.start_timestamp}",
        f"- Ended: {session.end_timestamp or 'In progress'}",
        f"- Mode: {session.mode}",
        "",
        "## Full Summary",
        "",
        session.full_summary or "Summary not generated yet.",
        "",
        "## Recaps",
        "",
    ]

    if recaps:
        for recap in recaps:
            lines.extend(
                [
                    f"### {recap.from_timestamp} to {recap.to_timestamp}",
                    "",
                    recap.summary,
                    "",
                    f"Keywords: {recap.key_str() or 'None'}",
                    "",
                ],
            )
    else:
        lines.extend(["No recaps generated yet.", ""])

    lines.extend(["## Transcript", ""])
    if transcript:
        lines.extend(
            f"- [{chunk.timestamp}] {chunk.text}" for chunk in transcript
        )
    else:
        lines.append("No transcript chunks captured.")

    return "\n".join(lines)


def build_pdf_export(bundle: SessionBundle) -> bytes:
    """Build a PDF byte stream from the session bundle."""
    session = bundle.session
    transcript = bundle.transcript
    recaps = bundle.recaps

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "SnapBack Notes Export", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Arial", "", 11)
    for line in [
        f"Session ID: {session.id}",
        f"Started: {session.start_timestamp}",
        f"Ended: {session.end_timestamp or 'In progress'}",
        f"Mode: {session.mode}",
        "",
        "Full Summary:",
        session.full_summary or "Summary not generated yet.",
        "",
        "Recaps:",
    ]:
        pdf.multi_cell(0, 7, fill(line, width=95) if line else "")

    if recaps:
        for recap in recaps:
            pdf.multi_cell(0, 7, fill(f"{recap.from_timestamp} to {recap.to_timestamp}", width=95))
            pdf.multi_cell(0, 7, fill(recap.summary, width=95))
            pdf.multi_cell(0, 7, fill(f"Keywords: {recap.key_str() or 'None'}", width=95))
            pdf.ln(2)
    else:
        pdf.multi_cell(0, 7, "No recaps generated yet.")

    pdf.multi_cell(0, 8, "Transcript:")
    for chunk in transcript:
        pdf.multi_cell(0, 7, fill(f"[{chunk.timestamp}] {chunk.text}", width=95))

    return bytes(pdf.output(dest="S"))


def export_to_notion(
    bundle: SessionBundle,
    api_key: str,
    page_id: str,
) -> dict:
    """Export the session bundle to a Notion page."""
    client = NotionClient(auth=api_key)
    session = bundle.session
    transcript = bundle.transcript
    recaps = bundle.recaps

    children: list[dict] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Lecture Summary"}},
                ],
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": session.full_summary or "None."}}],
            },
        },
    ]

    if recaps:
        children.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Recap History"}}]}})
        children.extend(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"{r.from_timestamp} to {r.to_timestamp}: {r.summary}"}}],
                },
            }
            for r in recaps
        )

    children.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Transcript"}}]}})
    p_view = "\n".join(f"[{c.timestamp}] {c.text}" for c in transcript[:50])
    children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": p_view or "No transcript."}}]}})

    page = client.pages.create(
        parent={"page_id": page_id},
        properties={"title": {"title": [{"type": "text", "text": {"content": f"SnapBack Session {session.start_timestamp[:10]}"}}]}},
        children=children,
    )
    return {"page_id": str(page["id"]), "url": str(page["url"])}
