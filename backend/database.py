from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator


DB_PATH = Path(__file__).resolve().parent / "data" / "snapback.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    ensure_parent_dir()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_timestamp TEXT NOT NULL,
                end_timestamp TEXT,
                full_summary TEXT,
                mode TEXT NOT NULL DEFAULT 'cloud',
                language TEXT NOT NULL DEFAULT 'English',
                recap_length TEXT NOT NULL DEFAULT 'standard',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transcript_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS recaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                from_timestamp TEXT NOT NULL,
                to_timestamp TEXT NOT NULL,
                summary TEXT NOT NULL,
                keywords_json TEXT NOT NULL,
                topic_shift_detected INTEGER NOT NULL DEFAULT 0,
                missed_alerts_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS audio_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'extension',
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            """
        )


def create_session(mode: str, language: str, recap_length: str) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    now = utc_now_iso()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (id, start_timestamp, mode, language, recap_length, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, now, mode, language, recap_length, now, now),
        )
    return get_session(session_id)


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def end_session(session_id: str, full_summary: str) -> dict[str, Any] | None:
    now = utc_now_iso()
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE sessions
            SET end_timestamp = ?, full_summary = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, full_summary, now, session_id),
        )
    return get_session(session_id)


def append_transcript_chunk(session_id: str, text: str, timestamp: str) -> dict[str, Any]:
    created_at = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO transcript_chunks (session_id, text, timestamp, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, text, timestamp, created_at),
        )
        chunk_id = cursor.lastrowid
        connection.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (created_at, session_id),
        )
        row = connection.execute(
            "SELECT * FROM transcript_chunks WHERE id = ?",
            (chunk_id,),
        ).fetchone()
    return dict(row)


def get_transcript(session_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, text, timestamp, created_at
            FROM transcript_chunks
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_transcript_window(session_id: str, from_timestamp: str, to_timestamp: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, text, timestamp, created_at
            FROM transcript_chunks
            WHERE session_id = ?
              AND timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC, id ASC
            """,
            (session_id, from_timestamp, to_timestamp),
        ).fetchall()
    return [dict(row) for row in rows]


def get_last_chunk_before(session_id: str, timestamp: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, session_id, text, timestamp, created_at
            FROM transcript_chunks
            WHERE session_id = ?
              AND timestamp < ?
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (session_id, timestamp),
        ).fetchone()
    return dict(row) if row else None


def get_first_chunk_after(session_id: str, timestamp: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, session_id, text, timestamp, created_at
            FROM transcript_chunks
            WHERE session_id = ?
              AND timestamp >= ?
            ORDER BY timestamp ASC, id ASC
            LIMIT 1
            """,
            (session_id, timestamp),
        ).fetchone()
    return dict(row) if row else None


def save_recap(
    session_id: str,
    from_timestamp: str,
    to_timestamp: str,
    summary: str,
    keywords: list[str],
    topic_shift_detected: bool,
    missed_alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    created_at = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recaps (
                session_id, from_timestamp, to_timestamp, summary,
                keywords_json, topic_shift_detected, missed_alerts_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                from_timestamp,
                to_timestamp,
                summary,
                json.dumps(keywords),
                1 if topic_shift_detected else 0,
                json.dumps(missed_alerts),
                created_at,
            ),
        )
        recap_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM recaps WHERE id = ?", (recap_id,)).fetchone()
    return hydrate_recap(dict(row))


def get_recaps(session_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM recaps
            WHERE session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
    return [hydrate_recap(dict(row)) for row in rows]


def hydrate_recap(row: dict[str, Any]) -> dict[str, Any]:
    row["keywords"] = json.loads(row.pop("keywords_json", "[]"))
    row["topic_shift_detected"] = bool(row["topic_shift_detected"])
    row["missed_alerts"] = json.loads(row.pop("missed_alerts_json", "[]"))
    return row


def save_audio_chunk(
    session_id: str,
    chunk_index: int,
    mime_type: str,
    file_path: str,
    timestamp: str,
    source: str = "extension",
) -> dict[str, Any]:
    created_at = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audio_chunks (session_id, chunk_index, mime_type, file_path, source, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, chunk_index, mime_type, file_path, source, timestamp, created_at),
        )
        chunk_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM audio_chunks WHERE id = ?", (chunk_id,)).fetchone()
    return dict(row)


def delete_sessions_older_than(hours: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_iso = cutoff.isoformat()
    with get_connection() as connection:
        session_rows = connection.execute(
            "SELECT id FROM sessions WHERE created_at < ?",
            (cutoff_iso,),
        ).fetchall()
        session_ids = [row["id"] for row in session_rows]
        if not session_ids:
            return 0
        placeholders = ",".join(["?"] * len(session_ids))
        connection.execute(f"DELETE FROM transcript_chunks WHERE session_id IN ({placeholders})", session_ids)
        connection.execute(f"DELETE FROM recaps WHERE session_id IN ({placeholders})", session_ids)
        connection.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", session_ids)
    return len(session_ids)


@dataclass
class SessionBundle:
    session: dict[str, Any]
    transcript: list[dict[str, Any]]
    recaps: list[dict[str, Any]]


def get_session_bundle(session_id: str) -> SessionBundle | None:
    session = get_session(session_id)
    if not session:
        return None
    return SessionBundle(
        session=session,
        transcript=get_transcript(session_id),
        recaps=get_recaps(session_id),
    )
