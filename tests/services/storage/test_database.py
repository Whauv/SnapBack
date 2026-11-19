"""Tests for the SQLite storage layer."""

from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        fd, name = tempfile.mkstemp(prefix="snapback-db-test-", suffix=".db")
        os.close(fd)
        self.db_path = Path(name)
        self.db_path.unlink(missing_ok=True)
        self._saved = os.environ.get("SNAPBACK_DB_PATH")
        os.environ["SNAPBACK_DB_PATH"] = str(self.db_path)
        self.db = importlib.reload(importlib.import_module("services.storage.database"))
        self.db.init_db()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)
        if self._saved is None:
            os.environ.pop("SNAPBACK_DB_PATH", None)
        else:
            os.environ["SNAPBACK_DB_PATH"] = self._saved
        importlib.reload(importlib.import_module("services.storage.database"))

    def _session(self) -> str:
        return self.db.create_session(owner_id="principal:alice", mode="cloud", language="English", recap_length="standard")["id"]

    def test_transcript_roundtrip_and_ordering(self):
        sid = self._session()
        self.db.append_transcript_chunk(sid, "second", "2026-04-07T10:01:00+00:00")
        self.db.append_transcript_chunk(sid, "first", "2026-04-07T10:00:00+00:00")
        transcript = self.db.get_transcript(sid)
        self.assertEqual([c["text"] for c in transcript], ["first", "second"])

    def test_transcript_window_and_neighbors(self):
        sid = self._session()
        for i in range(3):
            self.db.append_transcript_chunk(sid, f"chunk-{i}", f"2026-04-07T10:0{i}:00+00:00")
        window = self.db.get_transcript_window(sid, "2026-04-07T10:01:00+00:00", "2026-04-07T10:02:00+00:00")
        self.assertEqual([c["text"] for c in window], ["chunk-1", "chunk-2"])

        before = self.db.get_last_chunk_before(sid, "2026-04-07T10:01:00+00:00")
        self.assertEqual(before["text"], "chunk-0")
        after = self.db.get_first_chunk_after(sid, "2026-04-07T10:01:30+00:00")
        self.assertEqual(after["text"], "chunk-2")

    def test_recap_roundtrip_hydrates_json(self):
        sid = self._session()
        self.db.save_recap(
            session_id=sid,
            from_timestamp="2026-04-07T10:00:00+00:00",
            to_timestamp="2026-04-07T10:05:00+00:00",
            summary="Recap summary",
            keywords=["gradient", "descent"],
            topic_shift_detected=True,
            missed_alerts=[{"text": "exam"}],
        )
        recaps = self.db.get_recaps(sid)
        self.assertEqual(len(recaps), 1)
        self.assertEqual(recaps[0]["keywords"], ["gradient", "descent"])
        self.assertIs(recaps[0]["topic_shift_detected"], True)
        self.assertEqual(recaps[0]["missed_alerts"], [{"text": "exam"}])

    def test_owner_scope_on_get_session(self):
        sid = self._session()
        self.assertIsNotNone(self.db.get_session(sid, owner_id="principal:alice"))
        self.assertIsNone(self.db.get_session(sid, owner_id="principal:bob"))


if __name__ == "__main__":
    unittest.main()
