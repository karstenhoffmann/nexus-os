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
