from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    priority INTEGER NOT NULL,
    license TEXT NOT NULL,
    status TEXT NOT NULL,
    lock_json TEXT,
    accepted_bytes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS stats (
    source_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (source_id, metric)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    upstream_id TEXT NOT NULL,
    url TEXT,
    license TEXT NOT NULL,
    text TEXT NOT NULL,
    text_sha256 TEXT NOT NULL UNIQUE,
    byte_length INTEGER NOT NULL,
    char_length INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    lid_label TEXT,
    lid_score REAL,
    metrics_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    transformations_json TEXT NOT NULL,
    near_duplicate_of INTEGER,
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(near_duplicate_of) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_near_duplicate ON documents(near_duplicate_of);
"""


class CorpusStore:
    def __init__(self, path: Path, config_hash: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)

        existing = self.get_meta("config_hash")
        if existing is not None and existing != config_hash:
            raise RuntimeError(
                "The existing corpus database was built with another configuration. "
                "Run with --reset to rebuild it."
            )
        self.set_meta("config_hash", config_hash)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def get_meta(self, key: str) -> str | None:
        row = self.connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO meta(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def source_status(self, source_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT status FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        return str(row["status"]) if row else None

    def start_source(self, source: dict, lock: dict[str, Any]) -> None:
        source_id = source["id"]
        self.connection.execute("DELETE FROM documents WHERE source_id = ?", (source_id,))
        self.connection.execute("DELETE FROM stats WHERE source_id = ?", (source_id,))
        self.connection.execute(
            "INSERT INTO sources(source_id, priority, license, status, lock_json, accepted_bytes) "
            "VALUES (?, ?, ?, 'running', ?, 0) "
            "ON CONFLICT(source_id) DO UPDATE SET "
            "priority = excluded.priority, license = excluded.license, status = 'running', "
            "lock_json = excluded.lock_json, accepted_bytes = 0",
            (
                source_id,
                int(source["priority"]),
                source["license"],
                json.dumps(lock, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.connection.commit()

    def finish_source(self, source_id: str, accepted_bytes: int) -> None:
        self.connection.execute(
            "UPDATE sources SET status = 'complete', accepted_bytes = ? WHERE source_id = ?",
            (accepted_bytes, source_id),
        )
        self.connection.commit()

    def increment_stat(self, source_id: str, metric: str, amount: int = 1) -> None:
        self.connection.execute(
            "INSERT INTO stats(source_id, metric, value) VALUES (?, ?, ?) "
            "ON CONFLICT(source_id, metric) DO UPDATE SET value = value + excluded.value",
            (source_id, metric, amount),
        )

    def insert_document(
        self,
        *,
        source_id: str,
        upstream_id: str,
        url: str | None,
        license_name: str,
        text: str,
        text_sha256: str,
        metrics: dict[str, Any],
        metadata: dict[str, Any],
        transformations: dict[str, int],
        lid_label: str | None,
        lid_score: float | None,
    ) -> int | None:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO documents(
                source_id, upstream_id, url, license, text, text_sha256,
                byte_length, char_length, word_count, lid_label, lid_score,
                metrics_json, metadata_json, transformations_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                upstream_id,
                url,
                license_name,
                text,
                text_sha256,
                int(metrics["byte_length"]),
                int(metrics["char_length"]),
                int(metrics["word_count"]),
                lid_label,
                lid_score,
                json.dumps(metrics, ensure_ascii=False, sort_keys=True),
                json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str),
                json.dumps(transformations, ensure_ascii=False, sort_keys=True),
            ),
        )
        return int(cursor.lastrowid) if cursor.rowcount else None

    def commit(self) -> None:
        self.connection.commit()

    def reset_near_duplicates(self) -> None:
        self.connection.execute("UPDATE documents SET near_duplicate_of = NULL")
        self.connection.execute("DELETE FROM meta WHERE key = 'near_dedup_complete'")
        self.connection.commit()

    def mark_near_duplicate(self, document_id: int, retained_id: int) -> None:
        self.connection.execute(
            "UPDATE documents SET near_duplicate_of = ? WHERE id = ?",
            (retained_id, document_id),
        )

    def document_text(self, document_id: int) -> str:
        row = self.connection.execute(
            "SELECT text FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise KeyError(document_id)
        return str(row["text"])

    def iter_for_near_dedup(self):
        return self.connection.execute(
            """
            SELECT d.id, d.text
            FROM documents AS d
            JOIN sources AS s ON s.source_id = d.source_id
            ORDER BY s.priority ASC, d.lid_score DESC, d.byte_length DESC, d.text_sha256 ASC
            """
        )

    def iter_unique_source(self, source_id: str):
        return self.connection.execute(
            """
            SELECT * FROM documents
            WHERE source_id = ? AND near_duplicate_of IS NULL
            ORDER BY text_sha256 ASC
            """,
            (source_id,),
        )

    def source_summary(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT s.source_id, s.priority, s.license, s.status, s.accepted_bytes,
                   COUNT(d.id) AS exact_unique_docs,
                   COALESCE(SUM(CASE WHEN d.near_duplicate_of IS NULL THEN 1 ELSE 0 END), 0)
                       AS near_unique_docs,
                   COALESCE(SUM(CASE WHEN d.near_duplicate_of IS NULL THEN d.byte_length ELSE 0 END), 0)
                       AS near_unique_bytes
            FROM sources AS s
            LEFT JOIN documents AS d ON d.source_id = s.source_id
            GROUP BY s.source_id
            ORDER BY s.priority
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def stats_summary(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT source_id, metric, value FROM stats ORDER BY source_id, metric"
        ).fetchall()
        return [dict(row) for row in rows]

    def source_locks(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT source_id, lock_json FROM sources ORDER BY priority"
        ).fetchall()
        return [
            {"source_id": str(row["source_id"]), **json.loads(str(row["lock_json"]))}
            for row in rows
            if row["lock_json"]
        ]

    def quality_rows(self):
        return self.connection.execute(
            """
            SELECT source_id, byte_length, char_length, word_count, lid_score, text
            FROM documents
            WHERE near_duplicate_of IS NULL
            ORDER BY source_id, text_sha256
            """
        )

    def accepted_sample_rows(self, source_id: str, limit: int):
        return self.connection.execute(
            """
            SELECT source_id, upstream_id, url, text, lid_label, lid_score,
                   metrics_json, metadata_json
            FROM documents
            WHERE source_id = ? AND near_duplicate_of IS NULL
            ORDER BY text_sha256
            LIMIT ?
            """,
            (source_id, limit),
        )
