from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any

import sqlite_vec

from app.core.settings import Settings


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  provider_id TEXT,
  url_original TEXT,
  url_canonical TEXT,
  title TEXT,
  author TEXT,
  published_at TEXT,
  saved_at TEXT,
  fulltext TEXT,
  summary TEXT,
  raw_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(source, provider_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
  title, author, fulltext, summary,
  content='documents',
  content_rowid='id'
);

CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL,
  kind TEXT NOT NULL,
  title TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS draft_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
  version_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  note TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS digests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  query TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  input_json TEXT,
  output_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS import_jobs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  reader_cursor TEXT,
  export_cursor TEXT,
  reader_done INTEGER DEFAULT 0,
  export_done INTEGER DEFAULT 0,
  items_imported INTEGER DEFAULT 0,
  items_merged INTEGER DEFAULT 0,
  started_at TEXT DEFAULT (datetime('now')),
  last_activity TEXT DEFAULT (datetime('now')),
  error TEXT
);

CREATE TABLE IF NOT EXISTS highlights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  provider_highlight_id TEXT,
  text TEXT NOT NULL,
  note TEXT,
  highlighted_at TEXT,
  provider TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(document_id, provider_highlight_id)
);

CREATE INDEX IF NOT EXISTS idx_highlights_document_id ON highlights(document_id);
"""

VEC_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS doc_embeddings USING vec0(
  embedding float[1536],
  document_id integer
);
"""


@dataclass
class DB:
    conn: sqlite3.Connection

    def init(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.executescript(VEC_SQL)
        self.conn.commit()

    def get_stats(self) -> dict[str, Any]:
        cur = self.conn.execute("select count(*) from documents")
        docs = cur.fetchone()[0]
        cur = self.conn.execute("select count(*) from drafts")
        drafts = cur.fetchone()[0]
        cur = self.conn.execute("select count(*) from highlights")
        highlights = cur.fetchone()[0]
        return {"documents": docs, "drafts": drafts, "highlights": highlights}

    def search_documents(self, q: str) -> list[dict[str, Any]]:
        q = (q or "").strip()
        if not q:
            cur = self.conn.execute(
                "select id, title, author, url_original, saved_at from documents order by id desc limit 50"
            )
        else:
            cur = self.conn.execute(
                """
                select d.id, d.title, d.author, d.url_original, d.saved_at
                from documents_fts f
                join documents d on d.id = f.rowid
                where documents_fts match ?
                order by rank
                limit 50
                """,
                (q,),
            )
        rows = []
        for r in cur.fetchall():
            rows.append(
                {
                    "id": r[0],
                    "title": r[1],
                    "author": r[2],
                    "url": r[3],
                    "saved_at": r[4],
                }
            )
        return rows

    def list_digests(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("select id, name, query, created_at from digests order by id desc")
        return [{"id": r[0], "name": r[1], "query": r[2], "created_at": r[3]} for r in cur.fetchall()]

    def create_digest(self, name: str, query: str) -> None:
        self.conn.execute("insert into digests(name, query) values(?, ?)", (name.strip(), query.strip()))
        self.conn.commit()

    def list_drafts(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("select id, status, kind, title, updated_at from drafts order by id desc")
        return [{"id": r[0], "status": r[1], "kind": r[2], "title": r[3], "updated_at": r[4]} for r in cur.fetchall()]

    def save_article(
        self,
        *,
        source: str,
        provider_id: str,
        url_original: str | None,
        title: str | None,
        author: str | None = None,
        published_at: str | None = None,
        saved_at: str | None = None,
        fulltext: str | None = None,
        summary: str | None = None,
        raw_json: str | None = None,
    ) -> int:
        """Save or update an article in the documents table.

        Uses UPSERT logic: if an article with the same source+provider_id exists,
        it updates the existing record. Otherwise, inserts a new one.

        Returns the document id (existing or new).
        """
        cur = self.conn.execute(
            """
            INSERT INTO documents (source, provider_id, url_original, title, author, published_at, saved_at, fulltext, summary, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, provider_id) DO UPDATE SET
                url_original = COALESCE(excluded.url_original, url_original),
                title = COALESCE(excluded.title, title),
                author = COALESCE(excluded.author, author),
                published_at = COALESCE(excluded.published_at, published_at),
                saved_at = COALESCE(excluded.saved_at, saved_at),
                fulltext = COALESCE(excluded.fulltext, fulltext),
                summary = COALESCE(excluded.summary, summary),
                raw_json = COALESCE(excluded.raw_json, raw_json),
                updated_at = datetime('now')
            RETURNING id
            """,
            (source, provider_id, url_original, title, author, published_at, saved_at, fulltext, summary, raw_json),
        )
        row = cur.fetchone()
        self.conn.commit()
        doc_id = row[0] if row else 0
        # Update FTS index
        self._update_fts(doc_id)
        return doc_id

    def _update_fts(self, doc_id: int) -> None:
        """Update FTS index for a document."""
        # Delete old FTS entry if exists
        self.conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (doc_id,))
        # Insert new FTS entry
        self.conn.execute(
            """
            INSERT INTO documents_fts (rowid, title, author, fulltext, summary)
            SELECT id, title, author, fulltext, summary FROM documents WHERE id = ?
            """,
            (doc_id,),
        )
        self.conn.commit()

    def save_highlight(
        self,
        *,
        document_id: int,
        provider_highlight_id: str,
        text: str,
        note: str | None = None,
        highlighted_at: str | None = None,
        provider: str | None = None,
    ) -> int:
        """Save or update a highlight in the highlights table.

        Uses UPSERT logic: if a highlight with the same document_id+provider_highlight_id
        exists, it updates the existing record. Otherwise, inserts a new one.

        Returns the highlight id (existing or new).
        """
        # Use INSERT OR REPLACE with UNIQUE constraint
        cur = self.conn.execute(
            """
            INSERT INTO highlights (document_id, provider_highlight_id, text, note, highlighted_at, provider)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id, provider_highlight_id) DO UPDATE SET
                text = excluded.text,
                note = excluded.note,
                highlighted_at = excluded.highlighted_at,
                provider = excluded.provider
            RETURNING id
            """,
            (document_id, provider_highlight_id, text, note, highlighted_at, provider),
        )
        row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else 0

    def get_highlights_for_document(self, document_id: int) -> list[dict[str, Any]]:
        """Get all highlights for a document."""
        cur = self.conn.execute(
            """
            SELECT id, text, note, highlighted_at, provider
            FROM highlights
            WHERE document_id = ?
            ORDER BY highlighted_at DESC, id DESC
            """,
            (document_id,),
        )
        return [
            {
                "id": r[0],
                "text": r[1],
                "note": r[2],
                "highlighted_at": r[3],
                "provider": r[4],
            }
            for r in cur.fetchall()
        ]


_db: DB | None = None


def init_db() -> None:
    global _db
    from app.core.import_job import init_import_store

    s = Settings.from_env()
    os.makedirs(os.path.dirname(s.db_path), exist_ok=True)

    conn = sqlite3.connect(s.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # sqlite-vec must be loaded into this connection
    sqlite_vec.load(conn)

    _db = DB(conn=conn)
    _db.init()

    # Initialize import job store with same connection
    init_import_store(conn)


def get_db() -> DB:
    assert _db is not None, "DB not initialized"
    return _db
