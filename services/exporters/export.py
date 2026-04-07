from __future__ import annotations

from textwrap import fill
from typing import Any

try:
    from fpdf import FPDF
except Exception:  # pragma: no cover - optional dependency fallback
    FPDF = None
try:
    from notion_client import Client as NotionClient
except Exception:  # pragma: no cover - optional dependency fallback
    NotionClient = None


def build_markdown_export(bundle: dict[str, Any]) -> str:
    session = bundle["session"]
    transcript = bundle["transcript"]
    recaps = bundle["recaps"]

    lines = [
        f"# SnapBack Session {session['id']}",
        "",
        f"- Started: {session['start_timestamp']}",
        f"- Ended: {session.get('end_timestamp') or 'In progress'}",
        f"- Mode: {session.get('mode', 'cloud')}",
        "",
        "## Full Summary",
        "",
        session.get("full_summary") or "Summary not generated yet.",
        "",
        "## Recaps",
        "",
    ]

    if recaps:
        for recap in recaps:
            lines.extend(
                [
                    f"### {recap['from_timestamp']} to {recap['to_timestamp']}",
                    "",
                    recap["summary"],
                    "",
                    f"Keywords: {', '.join(recap['keywords']) or 'None'}",
                    "",
                ]
            )
    else:
        lines.extend(["No recaps generated yet.", ""])

    lines.extend(["## Transcript", ""])
    if transcript:
        for chunk in transcript:
            lines.append(f"- [{chunk['timestamp']}] {chunk['text']}")
    else:
        lines.append("No transcript chunks captured.")

    return "\n".join(lines)


def build_pdf_export(bundle: dict[str, Any]) -> bytes:
    if FPDF is None:
        raise RuntimeError("fpdf2 is not installed in this environment.")
    session = bundle["session"]
    transcript = bundle["transcript"]
    recaps = bundle["recaps"]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "SnapBack Notes Export", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Arial", "", 11)
    for line in [
        f"Session ID: {session['id']}",
        f"Started: {session['start_timestamp']}",
        f"Ended: {session.get('end_timestamp') or 'In progress'}",
        f"Mode: {session.get('mode', 'cloud')}",
        "",
        "Full Summary:",
        session.get("full_summary") or "Summary not generated yet.",
        "",
        "Recaps:",
    ]:
        pdf.multi_cell(0, 7, fill(line, width=95) if line else "")

    if recaps:
        for recap in recaps:
            pdf.multi_cell(0, 7, fill(f"{recap['from_timestamp']} to {recap['to_timestamp']}", width=95))
            pdf.multi_cell(0, 7, fill(recap["summary"], width=95))
            pdf.multi_cell(0, 7, fill(f"Keywords: {', '.join(recap['keywords']) or 'None'}", width=95))
            pdf.ln(2)
    else:
        pdf.multi_cell(0, 7, "No recaps generated yet.")

    pdf.multi_cell(0, 8, "Transcript:")
    for chunk in transcript:
        pdf.multi_cell(0, 7, fill(f"[{chunk['timestamp']}] {chunk['text']}", width=95))

    return bytes(pdf.output(dest="S"))


def export_to_notion(bundle: dict[str, Any], api_key: str, page_id: str) -> dict[str, Any]:
    if NotionClient is None:
        raise RuntimeError("notion-client is not installed in this environment.")
    client = NotionClient(auth=api_key)
    session = bundle["session"]
    transcript = bundle["transcript"]
    recaps = bundle["recaps"]

    children: list[dict[str, Any]] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Lecture Summary"}}]},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": session.get("full_summary") or "Summary not generated yet."}}
                ]
            },
        },
    ]

    if recaps:
        children.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Recap History"}}]},
            }
        )
        for recap in recaps:
            children.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{recap['from_timestamp']} to {recap['to_timestamp']}: {recap['summary']}"
                                },
                            }
                        ]
                    },
                }
            )

    children.append(
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Transcript"}}]},
        }
    )

    transcript_preview = "\n".join(f"[{chunk['timestamp']}] {chunk['text']}" for chunk in transcript[:50])
    children.append(
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": transcript_preview or "No transcript."}}]},
        }
    )

    page = client.pages.create(
        parent={"page_id": page_id},
        properties={
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": f"SnapBack Session {session['start_timestamp'][:10]}"},
                    }
                ]
            }
        },
        children=children,
    )
    return {"page_id": page["id"], "url": page["url"]}
