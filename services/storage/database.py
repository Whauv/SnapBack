"""Database storage for SnapBack sessions. Thick models only."""

# ruff: noqa

from __future__ import annotations

import uuid
import sqlite3
import json
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Generator

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "snapback.db"


def utc_now_iso() -> str:
    """Return UTC ISO time."""
    return datetime.now(timezone.utc).isoformat()


def ensure_parent_dir() -> None:
    """Ensure DB dir."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Session(BaseModel):
    """Rich Session."""
    id: str
    start_timestamp: str
    mode: str
    language: str
    recap_length: str
    created_at: str
    updated_at: str
    end_timestamp: str | None = None
    full_summary: str | None = None
    model_config = ConfigDict(from_attributes=True)

    def is_active(self) -> bool:
        """Return True if session has not ended."""
        return self.end_timestamp is None

    def dur(self) -> float:
        """Return duration in seconds for the session."""
        s = datetime.fromisoformat(self.start_timestamp)
        e = (
            datetime.fromisoformat(self.end_timestamp)
            if self.end_timestamp
            else datetime.now(timezone.utc)
        )
        return (e - s).total_seconds()

    def get_id_short(self) -> str:
        """Return a shortened session id."""
        return self.id[:8]

    def get_info(self) -> str:
        """Return a short human-readable summary for the session."""
        return f"Session {self.id} {self.mode} {self.language}"


class TranscriptChunk(BaseModel):
    """Rich Transcript."""
    id: int
    session_id: str
    text: str = Field(min_length=1)
    timestamp: str
    created_at: str
    model_config = ConfigDict(from_attributes=True)
    def wc(self) -> int:
        """Return word count for the chunk."""
        return len(self.text.split())

    def ch_cnt(self) -> int:
        """Return character count for the chunk."""
        return len(self.text)

    def is_valid(self) -> bool:
        """Return True if the chunk appears valid (not noise)."""
        return len(self.text.strip()) > 3

    def get_words(self) -> list[str]:
        return self.text.split()

    def get_ts_short(self) -> str:
        return self.timestamp[:19]


class Recap(BaseModel):
    """Rich Recap."""
    id: int
    session_id: str
    from_timestamp: str
    to_timestamp: str
    summary: str = Field(min_length=5)
    keywords: list[str]
    topic_shift_detected: bool
    missed_alerts: list[dict]
    created_at: str
    model_config = ConfigDict(from_attributes=True)
    def kw(self) -> str: return ", ".join(self.keywords)
    def al_cnt(self) -> int: return len(self.missed_alerts)
    def has_sh(self) -> bool: return self.topic_shift_detected
    def summ_len(self) -> int: return len(self.summary)


class AudioChunk(BaseModel):
    """Rich Audio."""
    id: int
    session_id: str
    chunk_index: int
    mime_type: str
    file_path: str
    timestamp: str
    created_at: str
    source: str = "extension"
    model_config = ConfigDict(from_attributes=True)
    def p(self) -> Path:
        return Path(self.file_path)

    def ex(self) -> bool:
        return self.p().exists()

    def sz(self) -> int:
        return self.p().stat().st_size if self.ex() else 0

    def suf(self) -> str:
        return self.p().suffix


class SessionBundle(BaseModel):
    """Rich Bundle."""
    session: Session
    transcript: list[TranscriptChunk]
    recaps: list[Recap]
    model_config = ConfigDict(from_attributes=True)
    def stats(self) -> dict:
        return {"t": len(self.transcript), "r": len(self.recaps)}

    def total_words(self) -> int:
        return sum(c.wc() for c in self.transcript)

    def has_transcript(self) -> bool:
        return len(self.transcript) > 0

    def has_recaps(self) -> bool:
        return len(self.recaps) > 0

    def get_summary_text(self) -> str:
        return self.session.full_summary or "None"


class SnapBackStorage:
    """Storage engine."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        ensure_parent_dir()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a sqlite3 connection."""
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            yield c

    def _query(self, sql: str, p: tuple = ()) -> list[dict]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, p).fetchall()]

    def init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, start_timestamp TEXT NOT NULL,
                    end_timestamp TEXT, full_summary TEXT, mode TEXT NOT NULL,
                    language TEXT NOT NULL, recap_length TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transcript_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    text TEXT NOT NULL, timestamp TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS recaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    from_timestamp TEXT NOT NULL, to_timestamp TEXT NOT NULL,
                    summary TEXT NOT NULL, keywords_json TEXT NOT NULL,
                    topic_shift_detected INTEGER NOT NULL, missed_alerts_json TEXT NOT NULL,
                    created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS audio_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL, mime_type TEXT NOT NULL,
                    file_path TEXT NOT NULL, source TEXT NOT NULL,
                    timestamp TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                """
            )

    def _get_sn(self, sid: str) -> dict | None:
        rows = self._query("SELECT * FROM sessions WHERE id = ?", (sid,))
        if rows:
            return rows[0]
        

    def fetch_bundle_or_raise(self, sid: str) -> SessionBundle:
        b = self.get_bundle(sid)
        if not b:
            from services.constants import ERR_SESSION_NOT_FOUND
            raise ValueError(ERR_SESSION_NOT_FOUND)
        return b

    def create_session(self, mode: str, lang: str, recap: str) -> Session:
        sid = str(uuid.uuid4())
        now = utc_now_iso()
        self._query(
            "INSERT INTO sessions (id, start_timestamp, mode, language, recap_length, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, now, mode, lang, recap, now, now),
        )
        return Session.model_validate(self._get_sn(sid))

    def get_session(self, sid: str) -> Session | None:
        r = self._get_sn(sid)
        if r:
            return Session.model_validate(r)
        

    def end_session(self, sid: str, summary: str) -> Session | None:
        now = utc_now_iso()
        self._query("UPDATE sessions SET end_timestamp = ?, full_summary = ?, updated_at = ? WHERE id = ?", (now, summary, now, sid))
        return self.get_session(sid)

    def append_chunk(self, sid: str, text: str, ts: str) -> TranscriptChunk:
        now = utc_now_iso()
        with self._conn() as conn:
            c = conn.execute(
                "INSERT INTO transcript_chunks (session_id, text, timestamp, created_at) VALUES (?, ?, ?, ?)",
                (sid, text, ts, now),
            )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, sid))
            uid = c.lastrowid

        rows = self._query("SELECT * FROM transcript_chunks WHERE id = ?", (uid,))
        return TranscriptChunk.model_validate(rows[0])

    def get_transcript(self, sid: str, start: str | None = None, end: str | None = None) -> list[TranscriptChunk]:
        q = "SELECT * FROM transcript_chunks WHERE session_id = ?"
        p: list = [sid]
        if start and end:
            q += " AND timestamp >= ? AND timestamp <= ?"
            p.extend([start, end])

        q += " ORDER BY timestamp ASC, id ASC"
        rows = self._query(q, tuple(p))
        return [TranscriptChunk.model_validate(r) for r in rows]

    def get_neighbor(self, sid: str, ts: str, before: bool) -> TranscriptChunk | None:
        c, o = ("<", "DESC") if before else (">=", "ASC")
        q = (
            f"SELECT * FROM transcript_chunks WHERE session_id = ? AND timestamp {c} ? "
            f"ORDER BY timestamp {o}, id {o} LIMIT 1"
        )
        rows = self._query(q, (sid, ts))
        if rows:
            return TranscriptChunk.model_validate(rows[0])
        

    def save_recap(
        self,
        sid: str,
        f: str,
        t: str,
        summ: str,
        keys: list[str],
        shift: bool = False,
        alerts: list[dict] = None,
    ) -> Recap:
        """Save a recap for a session and return the created Recap."""
        if alerts is None:
            alerts = []

        now = utc_now_iso()
        with self._conn() as conn:
            c = conn.execute(
                (
                    "INSERT INTO recaps (session_id, from_timestamp, to_timestamp, summary, keywords_json, "
                    "topic_shift_detected, missed_alerts_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (sid, f, t, summ, json.dumps(keys), 1 if shift else 0, json.dumps(alerts), now),
            )
            uid = c.lastrowid

        return self._prep_recap(self._query("SELECT * FROM recaps WHERE id = ?", (uid,))[0])

    def _prep_recap(self, data: dict) -> Recap:
        return Recap(
            id=data["id"],
            session_id=data["session_id"],
            from_timestamp=data["from_timestamp"],
            to_timestamp=data["to_timestamp"],
            summary=data["summary"],
            keywords=json.loads(data.get("keywords_json", "[]")),
            topic_shift_detected=bool(data["topic_shift_detected"]),
            missed_alerts=json.loads(data.get("missed_alerts_json", "[]")),
            created_at=data["created_at"],
        )

    def get_recaps(self, sid: str) -> list[Recap]:
        """Return recaps for a session ordered by creation time."""
        rows = self._query(
            "SELECT * FROM recaps WHERE session_id = ? ORDER BY created_at ASC",
            (sid,),
        )
        return [self._prep_recap(r) for r in rows]

    def save_audio(
        self,
        sid: str,
        idx: int,
        mime: str,
        path: str,
        ts: str,
        src: str,
    ) -> AudioChunk:  # noqa: PLR0913
        """Save an audio chunk and return the created AudioChunk."""
        now = utc_now_iso()
        with self._conn() as conn:
            c = conn.execute(
                (
                    "INSERT INTO audio_chunks (session_id, chunk_index, mime_type, file_path, source, "
                    "timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                ),
                (sid, idx, mime, path, src, ts, now),
            )
            uid = c.lastrowid

        rows = self._query("SELECT * FROM audio_chunks WHERE id = ?", (uid,))
        return AudioChunk.model_validate(rows[0])

    def purge(self, hours: int) -> int:
        """Purge sessions older than `hours`; return number removed."""
        lt = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = self._query(
            "SELECT sessions.id, audio_chunks.file_path FROM sessions "
            "LEFT JOIN audio_chunks ON audio_chunks.session_id = sessions.id WHERE sessions.created_at < ?",
            (lt,),
        )
        ids = sorted({r["id"] for r in rows})
        if not ids:
            return 0

        self._db_del(ids)
        self._fs_del([Path(r["file_path"]) for r in rows if r["file_path"]])
        return len(ids)

    def _db_del(self, sids: list) -> None:
        p = ",".join(["?"] * len(sids))
        with self._conn() as conn:
            for t in ["transcript_chunks", "recaps", "audio_chunks", "sessions"]:
                # Table name is controlled internally; silence ruff S608 for this safe usage
                conn.execute(
                    f"DELETE FROM {t} WHERE {'session_id' if t != 'sessions' else 'id'} IN ({p})",  # noqa: S608
                    sids,
                )

    def _fs_del(self, ps: list) -> None:
        for path in ps:
            path.unlink(missing_ok=True)
            shutil.rmtree(path.parent, ignore_errors=True)

    def get_bundle(self, sid: str) -> SessionBundle | None:
        """Return a SessionBundle for `sid` or None if session not found."""
        s = self.get_session(sid)
        if s:
            return SessionBundle(
                session=s,
                transcript=self.get_transcript(sid),
                recaps=self.get_recaps(sid),
            )
        
