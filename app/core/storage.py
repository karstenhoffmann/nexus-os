from __future__ import annotations

import hashlib
import os
import sqlite3
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import sqlite_vec

from app.core.settings import Settings


def normalize_url(url: str | None) -> str | None:
    """Normalize URL for deduplication.

    - Convert to lowercase
    - Remove www. prefix
    - Remove trailing slash
    - Normalize http to https
    - Remove query parameters and fragments
    """
    if not url:
        return None
    url = url.strip().lower()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    parsed = urlparse(url)
    # Remove www. prefix and rebuild without query/fragment
    netloc = parsed.netloc.replace("www.", "")
    normalized = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path.rstrip("/"),
        "",  # params
        "",  # query
        "",  # fragment
    ))
    return normalized or None


def normalize_highlight_text(text: str) -> str:
    """Normalize text for hash comparison.

    - Unicode NFC normalization
    - Normalize whitespace (multiple spaces → single space)
    - Trim
    """
    text = unicodedata.normalize("NFC", text)
    text = " ".join(text.split())
    return text


def text_hash(text: str) -> str:
    """Generate hash for highlight text deduplication."""
    normalized = normalize_highlight_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


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
  items_failed INTEGER DEFAULT 0,
  items_total INTEGER,
  started_at TEXT DEFAULT (datetime('now')),
  last_activity TEXT DEFAULT (datetime('now')),
  error TEXT
);

CREATE TABLE IF NOT EXISTS highlights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  provider_highlight_id TEXT,
  text TEXT NOT NULL,
  text_hash TEXT,
  note TEXT,
  highlighted_at TEXT,
  provider TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(document_id, text_hash)
);

CREATE INDEX IF NOT EXISTS idx_highlights_document_id ON highlights(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_source_url ON documents(source, url_canonical);
"""

def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run schema migrations for existing DBs."""
    # Check if provider_id column exists in documents table
    cur = conn.execute("PRAGMA table_info(documents)")
    columns = {row[1] for row in cur.fetchall()}

    if "provider_id" not in columns:
        # Add provider_id column
        conn.execute("ALTER TABLE documents ADD COLUMN provider_id TEXT")
        # Create unique index (can't add UNIQUE constraint to existing table)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_source_provider "
            "ON documents(source, provider_id)"
        )
        conn.commit()

    # Check if items_total column exists in import_jobs table
    cur = conn.execute("PRAGMA table_info(import_jobs)")
    job_columns = {row[1] for row in cur.fetchall()}

    if "items_total" not in job_columns:
        conn.execute("ALTER TABLE import_jobs ADD COLUMN items_total INTEGER")
        conn.commit()

    if "items_failed" not in job_columns:
        conn.execute("ALTER TABLE import_jobs ADD COLUMN items_failed INTEGER DEFAULT 0")
        conn.commit()

    # Check if text_hash column exists in highlights table
    cur = conn.execute("PRAGMA table_info(highlights)")
    highlight_columns = {row[1] for row in cur.fetchall()}

    if "text_hash" not in highlight_columns:
        conn.execute("ALTER TABLE highlights ADD COLUMN text_hash TEXT")
        conn.commit()

    # Create index on documents(source, url_canonical) if not exists
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_source_url "
        "ON documents(source, url_canonical)"
    )
    conn.commit()

    # Create FTS table if not exists (for existing DBs without FTS)
    # Check if FTS table exists by trying to query it
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'"
    )
    fts_exists = cur.fetchone() is not None

    if not fts_exists:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, author, fulltext, summary,
                content='documents',
                content_rowid='id'
            )
            """
        )
        conn.commit()

        # Populate FTS index if documents exist
        cur = conn.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        if doc_count > 0:
            conn.execute(
                """
                INSERT INTO documents_fts (rowid, title, author, fulltext, summary)
                SELECT id, title, author, fulltext, summary FROM documents
                """
            )
            conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('optimize')")
            conn.commit()

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
        # Run migrations for existing DBs
        _run_migrations(self.conn)

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

    def get_document(self, doc_id: int) -> dict[str, Any] | None:
        """Get a single document by ID."""
        cur = self.conn.execute(
            """
            SELECT id, source, provider_id, url_original, title, author,
                   published_at, saved_at, fulltext, summary, created_at
            FROM documents WHERE id = ?
            """,
            (doc_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "source": row[1],
            "provider_id": row[2],
            "url_original": row[3],
            "title": row[4],
            "author": row[5],
            "published_at": row[6],
            "saved_at": row[7],
            "fulltext": row[8],
            "summary": row[9],
            "created_at": row[10],
        }

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

        Deduplication strategy (within same source/provider):
        1. First try to find existing document by normalized URL
        2. If found: update that document
        3. If not found: UPSERT by provider_id (fallback)

        This prevents duplicates when the same content has different provider_ids
        but the same URL (common with Snipd/Readwise).

        Returns the document id (existing or new).
        """
        url_canonical = normalize_url(url_original)

        # 1. Try to find existing document by URL (within same source)
        existing_id = None
        if url_canonical:
            cur = self.conn.execute(
                "SELECT id FROM documents WHERE source = ? AND url_canonical = ?",
                (source, url_canonical),
            )
            row = cur.fetchone()
            if row:
                existing_id = row[0]

        if existing_id:
            # 2. Update existing document (found by URL)
            self.conn.execute(
                """
                UPDATE documents SET
                    provider_id = ?,
                    url_original = COALESCE(?, url_original),
                    url_canonical = ?,
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
                (provider_id, url_original, url_canonical, title, author,
                 published_at, saved_at, fulltext, summary, raw_json, existing_id),
            )
            self.conn.commit()
            return existing_id

        # 3. No URL match - UPSERT by provider_id (fallback for docs without URL)
        cur = self.conn.execute(
            """
            INSERT INTO documents (source, provider_id, url_original, url_canonical, title, author, published_at, saved_at, fulltext, summary, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, provider_id) DO UPDATE SET
                url_original = COALESCE(excluded.url_original, url_original),
                url_canonical = COALESCE(excluded.url_canonical, url_canonical),
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
            (source, provider_id, url_original, url_canonical, title, author,
             published_at, saved_at, fulltext, summary, raw_json),
        )
        row = cur.fetchone()
        self.conn.commit()
        doc_id = row[0] if row else 0
        # FTS index will be rebuilt after import via rebuild_fts()
        return doc_id

    def rebuild_fts(self) -> int:
        """Rebuild the entire FTS index from the documents table.

        This is more efficient than updating row-by-row and avoids
        conflicts with sqlite-vec during bulk imports.

        Returns the number of documents indexed.
        """
        # Clear and rebuild the FTS index
        self.conn.execute("DELETE FROM documents_fts")
        self.conn.execute(
            """
            INSERT INTO documents_fts (rowid, title, author, fulltext, summary)
            SELECT id, title, author, fulltext, summary FROM documents
            """
        )
        # Optimize the FTS index
        self.conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('optimize')")
        self.conn.commit()

        cur = self.conn.execute("SELECT COUNT(*) FROM documents_fts")
        return cur.fetchone()[0]

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

        Deduplication by text_hash: if the same text (normalized) already exists
        for this document, update instead of creating a duplicate.

        This prevents duplicate highlights when the same content is imported
        multiple times with different provider_highlight_ids.

        Returns the highlight id (existing or new).
        """
        th = text_hash(text)

        cur = self.conn.execute(
            """
            INSERT INTO highlights (document_id, text_hash, provider_highlight_id, text, note, highlighted_at, provider)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id, text_hash) DO UPDATE SET
                provider_highlight_id = COALESCE(excluded.provider_highlight_id, provider_highlight_id),
                text = excluded.text,
                note = COALESCE(excluded.note, note),
                highlighted_at = COALESCE(excluded.highlighted_at, highlighted_at),
                provider = COALESCE(excluded.provider, provider)
            RETURNING id
            """,
            (document_id, th, provider_highlight_id, text, note, highlighted_at, provider),
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
