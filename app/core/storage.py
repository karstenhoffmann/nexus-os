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
  updated_at TEXT DEFAULT (datetime('now'))
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
        return {"documents": docs, "drafts": drafts}

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
        # Check if article already exists by source+provider_id
        # We store provider_id in the id field as "source:provider_id" format
        # But we need a separate lookup mechanism - use raw_json or url_original

        # First, try to find existing by source URL (normalized)
        existing_id = None
        if url_original:
            cur = self.conn.execute(
                "SELECT id FROM documents WHERE url_original = ? AND source = ?",
                (url_original, source),
            )
            row = cur.fetchone()
            if row:
                existing_id = row[0]

        if existing_id:
            # Update existing record
            self.conn.execute(
                """
                UPDATE documents SET
                    title = COALESCE(?, title),
                    author = COALESCE(?, author),
                    published_at = COALESCE(?, published_at),
                    saved_at = COALESCE(?, saved_at),
                    fulltext = COALESCE(?, fulltext),
                    summary = COALESCE(?, summary),
                    raw_json = COALESCE(?, raw_json),
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (title, author, published_at, saved_at, fulltext, summary, raw_json, existing_id),
            )
            self.conn.commit()
            # Update FTS index
            self._update_fts(existing_id)
            return existing_id
        else:
            # Insert new record
            cur = self.conn.execute(
                """
                INSERT INTO documents (source, url_original, title, author, published_at, saved_at, fulltext, summary, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source, url_original, title, author, published_at, saved_at, fulltext, summary, raw_json),
            )
            self.conn.commit()
            doc_id = cur.lastrowid
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


_db: DB | None = None


def init_db() -> None:
    global _db
    s = Settings.from_env()
    os.makedirs(os.path.dirname(s.db_path), exist_ok=True)

    conn = sqlite3.connect(s.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # sqlite-vec must be loaded into this connection
    sqlite_vec.load(conn)

    _db = DB(conn=conn)
    _db.init()


def get_db() -> DB:
    assert _db is not None, "DB not initialized"
    return _db
