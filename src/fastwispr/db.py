from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS dictionary (
  id INTEGER PRIMARY KEY,
  term TEXT NOT NULL UNIQUE,
  replacement TEXT NOT NULL,
  hint TEXT,
  tags TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS snippets (
  id INTEGER PRIMARY KEY,
  cue TEXT NOT NULL UNIQUE,
  body TEXT NOT NULL,
  app_scope TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dictation_events (
  id INTEGER PRIMARY KEY,
  app_name TEXT,
  raw_transcript TEXT,
  final_text TEXT,
  latency_ms INTEGER,
  stt_latency_ms INTEGER,
  audio_duration_ms INTEGER,
  language TEXT,
  language_probability REAL,
  audio_rms REAL,
  audio_peak REAL,
  skipped_reason TEXT,
  stt_model TEXT,
  polish_model TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

DICTATION_EVENT_COLUMNS: dict[str, str] = {
    "stt_latency_ms": "INTEGER",
    "audio_duration_ms": "INTEGER",
    "language": "TEXT",
    "language_probability": "REAL",
    "audio_rms": "REAL",
    "audio_peak": "REAL",
    "skipped_reason": "TEXT",
}


@dataclass(frozen=True)
class DictionaryEntry:
    term: str
    replacement: str


@dataclass(frozen=True)
class Snippet:
    cue: str
    body: str
    app_scope: str | None = None


@dataclass(frozen=True)
class DictationEvent:
    id: int
    final_text: str
    latency_ms: int | None
    stt_latency_ms: int | None
    audio_duration_ms: int | None
    language: str | None
    language_probability: float | None
    audio_rms: float | None
    audio_peak: float | None
    skipped_reason: str | None
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "final_text": self.final_text,
            "latency_ms": self.latency_ms,
            "stt_latency_ms": self.stt_latency_ms,
            "audio_duration_ms": self.audio_duration_ms,
            "language": self.language,
            "language_probability": self.language_probability,
            "audio_rms": self.audio_rms,
            "audio_peak": self.audio_peak,
            "skipped_reason": self.skipped_reason,
            "created_at": self.created_at,
        }


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def init_schema(self) -> None:
        with self.lock:
            self.conn.executescript(SCHEMA)
            self._ensure_dictation_event_columns()
            self.conn.commit()

    def _ensure_dictation_event_columns(self) -> None:
        existing = {row["name"] for row in self.conn.execute("PRAGMA table_info(dictation_events)").fetchall()}
        for column, column_type in DICTATION_EVENT_COLUMNS.items():
            if column not in existing:
                self.conn.execute(f"ALTER TABLE dictation_events ADD COLUMN {column} {column_type}")

    def upsert_dictionary(self, term: str, replacement: str, hint: str | None = None, tags: str | None = None) -> None:
        cleaned_term = term.strip()
        if not cleaned_term:
            raise ValueError("Dictionary term cannot be empty")
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO dictionary(term, replacement, hint, tags)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(term) DO UPDATE SET
                  replacement = excluded.replacement,
                  hint = excluded.hint,
                  tags = excluded.tags,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (cleaned_term, replacement.strip(), hint, tags),
            )
            self.conn.commit()

    def dictionary_entries(self) -> list[DictionaryEntry]:
        with self.lock:
            rows = self.conn.execute("SELECT term, replacement FROM dictionary ORDER BY length(term) DESC, term").fetchall()
        return [DictionaryEntry(row["term"], row["replacement"]) for row in rows]

    def delete_dictionary(self, term: str) -> int:
        with self.lock:
            cursor = self.conn.execute("DELETE FROM dictionary WHERE term = ?", (term.strip(),))
            self.conn.commit()
        return cursor.rowcount

    def upsert_snippet(self, cue: str, body: str, app_scope: str | None = None, enabled: bool = True) -> None:
        cleaned_cue = cue.strip()
        if not cleaned_cue:
            raise ValueError("Snippet cue cannot be empty")
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO snippets(cue, body, app_scope, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cue) DO UPDATE SET
                  body = excluded.body,
                  app_scope = excluded.app_scope,
                  enabled = excluded.enabled,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (cleaned_cue, body, app_scope, 1 if enabled else 0),
            )
            self.conn.commit()

    def snippets(self, app_name: str | None = None) -> list[Snippet]:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT cue, body, app_scope FROM snippets
                WHERE enabled = 1 AND (app_scope IS NULL OR app_scope = ?)
                ORDER BY length(cue) DESC, cue
                """,
                (app_name,),
            ).fetchall()
        return [Snippet(row["cue"], row["body"], row["app_scope"]) for row in rows]

    def set_setting(self, key: str, value: str) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            self.conn.commit()

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def record_dictation_event(
        self,
        *,
        raw_transcript: str | None,
        final_text: str,
        latency_ms: int,
        stt_latency_ms: int | None = None,
        audio_duration_ms: int | None = None,
        language: str | None = None,
        language_probability: float | None = None,
        audio_rms: float | None = None,
        audio_peak: float | None = None,
        skipped_reason: str | None = None,
        app_name: str | None = None,
        stt_model: str | None = None,
        polish_model: str | None = None,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO dictation_events(
                  app_name, raw_transcript, final_text, latency_ms, stt_latency_ms,
                  audio_duration_ms, language, language_probability, audio_rms, audio_peak,
                  skipped_reason, stt_model, polish_model
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    app_name,
                    raw_transcript,
                    final_text,
                    latency_ms,
                    stt_latency_ms,
                    audio_duration_ms,
                    language,
                    language_probability,
                    audio_rms,
                    audio_peak,
                    skipped_reason,
                    stt_model,
                    polish_model,
                ),
            )
            self.conn.commit()

    def recent_dictation_events(
        self,
        limit: int = 10,
        *,
        skipped_only: bool = False,
        language: str | None = None,
    ) -> list[DictationEvent]:
        where = []
        params: list[object] = []
        if skipped_only:
            where.append("skipped_reason IS NOT NULL")
        if language:
            where.append("language = ?")
            params.append(language)
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        params.append(max(1, limit))
        with self.lock:
            rows = self.conn.execute(
                f"""
                SELECT id, final_text, latency_ms, stt_latency_ms, audio_duration_ms,
                       language, language_probability, audio_rms, audio_peak, skipped_reason, created_at
                FROM dictation_events
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [dictation_event_from_row(row) for row in rows]


def dictation_event_from_row(row: sqlite3.Row | dict[str, Any]) -> DictationEvent:
    return DictationEvent(
        id=int(row["id"]),
        final_text=row["final_text"] or "",
        latency_ms=row["latency_ms"],
        stt_latency_ms=row["stt_latency_ms"],
        audio_duration_ms=row["audio_duration_ms"],
        language=row["language"],
        language_probability=row["language_probability"],
        audio_rms=row["audio_rms"],
        audio_peak=row["audio_peak"],
        skipped_reason=row["skipped_reason"],
        created_at=row["created_at"],
    )


def init_db(path: str | Path) -> None:
    with Store(path):
        pass
