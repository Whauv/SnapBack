"""Tests for the export builders (Markdown, PDF, Notion)."""

from __future__ import annotations

import unittest
from unittest import mock

from services.exporters import export

BUNDLE = {
    "session": {
        "id": "sess-1",
        "start_timestamp": "2026-04-07T10:00:00+00:00",
        "end_timestamp": None,
        "mode": "cloud",
        "full_summary": "A short recap of gradient descent.",
    },
    "transcript": [
        {"timestamp": "2026-04-07T10:00:00+00:00", "text": "Intro to gradient descent."},
    ],
    "recaps": [
        {
            "from_timestamp": "2026-04-07T10:00:00+00:00",
            "to_timestamp": "2026-04-07T10:05:00+00:00",
            "summary": "Covered the cost function.",
            "keywords": ["gradient", "descent"],
        }
    ],
}


class MarkdownExportTests(unittest.TestCase):
    def test_contains_sections_and_content(self):
        markdown = export.build_markdown_export(BUNDLE)
        self.assertIn("# SnapBack Session sess-1", markdown)
        self.assertIn("## Full Summary", markdown)
        self.assertIn("Covered the cost function.", markdown)
        self.assertIn("Intro to gradient descent.", markdown)
        self.assertIn("Keywords: gradient, descent", markdown)


class PdfExportTests(unittest.TestCase):
    def test_returns_pdf_bytes(self):
        pdf_bytes = export.build_pdf_export(BUNDLE)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


class NotionExportTests(unittest.TestCase):
    def test_creates_page_with_mocked_client(self):
        fake_page = {"id": "page-xyz", "url": "https://notion.so/page-xyz"}
        fake_client = mock.MagicMock()
        fake_client.pages.create.return_value = fake_page

        with mock.patch.object(export, "NotionClient", return_value=fake_client) as client_cls:
            result = export.export_to_notion(BUNDLE, api_key="secret", page_id="parent-1")

        client_cls.assert_called_once_with(auth="secret")
        self.assertEqual(result, {"page_id": "page-xyz", "url": "https://notion.so/page-xyz"})
        _, kwargs = fake_client.pages.create.call_args
        self.assertEqual(kwargs["parent"], {"page_id": "parent-1"})
        self.assertTrue(kwargs["children"])  # heading + summary + transcript blocks


if __name__ == "__main__":
    unittest.main()
