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

-- Chunks mit Positionsdaten fuer Zitierbarkeit
CREATE TABLE IF NOT EXISTS document_chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  char_start INTEGER NOT NULL,
  char_end INTEGER NOT NULL,
  token_count INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);

-- Embeddings mit Provider-Info (unterstuetzt mehrere Provider/Modelle)
CREATE TABLE IF NOT EXISTS embeddings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
  chunk_id INTEGER REFERENCES document_chunks(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  embedding BLOB NOT NULL,
  dimensions INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  CHECK (document_id IS NOT NULL OR chunk_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_provider_model ON embeddings(provider, model);
-- Combined index for efficient "chunks without embedding" queries
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_provider_model ON embeddings(chunk_id, provider, model);

-- API Usage Tracking (fuer Kosten-Dashboard)
CREATE TABLE IF NOT EXISTS api_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  operation TEXT NOT NULL,
  tokens_input INTEGER NOT NULL,
  tokens_output INTEGER DEFAULT 0,
  cost_usd REAL NOT NULL,
  latency_ms INTEGER,
  success INTEGER NOT NULL DEFAULT 1,
  error_message TEXT,
  metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON api_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON api_usage(provider);
CREATE INDEX IF NOT EXISTS idx_usage_operation ON api_usage(operation);

-- FTS fuer Chunks (Hybrid-Suche)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  chunk_text,
  content='document_chunks',
  content_rowid='id'
);

-- Fulltext Fetch Jobs
CREATE TABLE IF NOT EXISTS fetch_jobs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,  -- pending, running, paused, cancelled, completed, failed
  cursor_doc_id INTEGER,  -- Resume-Position
  items_processed INTEGER DEFAULT 0,
  items_succeeded INTEGER DEFAULT 0,
  items_failed INTEGER DEFAULT 0,
  items_skipped INTEGER DEFAULT 0,
  items_total INTEGER,
  started_at TEXT DEFAULT (datetime('now')),
  last_activity TEXT DEFAULT (datetime('now')),
  error TEXT
);

-- Fetch Failures mit Error-Klassifizierung
CREATE TABLE IF NOT EXISTS fetch_failures (
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  job_id TEXT REFERENCES fetch_jobs(id),
  url TEXT NOT NULL,
  error_type TEXT NOT NULL,  -- timeout, http_4xx, http_5xx, paywall, js_required, extraction_failed
  error_message TEXT,
  http_status INTEGER,
  retry_count INTEGER DEFAULT 0,
  last_attempt TEXT DEFAULT (datetime('now')),
  next_retry_after TEXT,
  UNIQUE(document_id)
);

CREATE INDEX IF NOT EXISTS idx_fetch_failures_error_type ON fetch_failures(error_type);
CREATE INDEX IF NOT EXISTS idx_fetch_failures_job_id ON fetch_failures(job_id);

-- Embedding Jobs (SSE-basiertes System)
CREATE TABLE IF NOT EXISTS embed_jobs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,  -- pending, running, paused, cancelled, completed, failed
  cursor_chunk_id INTEGER,  -- Resume-Position (letzter verarbeiteter Chunk)
  items_processed INTEGER DEFAULT 0,
  items_succeeded INTEGER DEFAULT 0,
  items_failed INTEGER DEFAULT 0,
  items_total INTEGER,
  tokens_used INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0,
  provider TEXT DEFAULT 'openai',
  model TEXT DEFAULT 'text-embedding-3-small',
  started_at TEXT DEFAULT (datetime('now')),
  last_activity TEXT DEFAULT (datetime('now')),
  error TEXT
);

-- App Settings (Key-Value Store fuer Theme etc.)
CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT DEFAULT (datetime('now'))
);
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

    # Add fulltext tracking columns to documents (for fetch feature)
    if "fulltext_fetched_at" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN fulltext_fetched_at TEXT")
        conn.commit()

    if "fulltext_source" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN fulltext_source TEXT")
        conn.commit()

    # Add fulltext_html column (preserves original HTML from Readwise)
    if "fulltext_html" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN fulltext_html TEXT")
        conn.commit()

    # Add combined index for efficient "chunks without embedding" queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_provider_model
        ON embeddings(chunk_id, provider, model)
    """)
    conn.commit()

    # Create embed_jobs table if not exists (for SSE-based embedding system)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='embed_jobs'"
    )
    if cur.fetchone() is None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embed_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                cursor_chunk_id INTEGER,
                items_processed INTEGER DEFAULT 0,
                items_succeeded INTEGER DEFAULT 0,
                items_failed INTEGER DEFAULT 0,
                items_total INTEGER,
                tokens_used INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                provider TEXT DEFAULT 'openai',
                model TEXT DEFAULT 'text-embedding-3-small',
                started_at TEXT DEFAULT (datetime('now')),
                last_activity TEXT DEFAULT (datetime('now')),
                error TEXT
            )
        """)
        conn.commit()

    # Create app_settings table if not exists (for theme etc.)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='app_settings'"
    )
    if cur.fetchone() is None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


VEC_SQL = """
-- Legacy table (kept for backward compatibility)
CREATE VIRTUAL TABLE IF NOT EXISTS doc_embeddings USING vec0(
  embedding float[1536],
  document_id integer
);

-- Vec0 Tabellen pro Dimension (fuer verschiedene Modelle)
-- 768: Ollama nomic-embed-text
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings_768 USING vec0(
  embedding float[768],
  +embedding_id INTEGER
);

-- 1024: Ollama mxbai-embed-large
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings_1024 USING vec0(
  embedding float[1024],
  +embedding_id INTEGER
);

-- 1536: OpenAI text-embedding-3-small
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings_1536 USING vec0(
  embedding float[1536],
  +embedding_id INTEGER
);

-- 3072: OpenAI text-embedding-3-large
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings_3072 USING vec0(
  embedding float[3072],
  +embedding_id INTEGER
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
        fulltext_html: str | None = None,
        fulltext_source: str | None = None,
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

        Args:
            fulltext: Clean text for search/chunking/embedding
            fulltext_html: Original HTML from source (preserved for rich display)
            fulltext_source: Source of fulltext ('readwise', 'trafilatura', 'manual')

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
            # Only update fulltext_source and fulltext_fetched_at if new fulltext is provided
            if fulltext:
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
                        fulltext = ?,
                        fulltext_html = COALESCE(?, fulltext_html),
                        fulltext_source = ?,
                        fulltext_fetched_at = datetime('now'),
                        summary = COALESCE(?, summary),
                        raw_json = COALESCE(?, raw_json),
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (provider_id, url_original, url_canonical, title, author,
                     published_at, saved_at, fulltext, fulltext_html, fulltext_source, summary, raw_json, existing_id),
                )
            else:
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
                        fulltext_html = COALESCE(?, fulltext_html),
                        summary = COALESCE(?, summary),
                        raw_json = COALESCE(?, raw_json),
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (provider_id, url_original, url_canonical, title, author,
                     published_at, saved_at, fulltext_html, summary, raw_json, existing_id),
                )
            self.conn.commit()
            return existing_id

        # 3. No URL match - UPSERT by provider_id (fallback for docs without URL)
        # Set fulltext_fetched_at only if fulltext is provided
        fulltext_fetched_at = "datetime('now')" if fulltext else None
        cur = self.conn.execute(
            """
            INSERT INTO documents (
                source, provider_id, url_original, url_canonical, title, author,
                published_at, saved_at, fulltext, fulltext_html, fulltext_source, fulltext_fetched_at, summary, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ? IS NOT NULL THEN datetime('now') END, ?, ?)
            ON CONFLICT(source, provider_id) DO UPDATE SET
                url_original = COALESCE(excluded.url_original, url_original),
                url_canonical = COALESCE(excluded.url_canonical, url_canonical),
                title = COALESCE(excluded.title, title),
                author = COALESCE(excluded.author, author),
                published_at = COALESCE(excluded.published_at, published_at),
                saved_at = COALESCE(excluded.saved_at, saved_at),
                fulltext = COALESCE(excluded.fulltext, fulltext),
                fulltext_html = COALESCE(excluded.fulltext_html, fulltext_html),
                fulltext_source = CASE WHEN excluded.fulltext IS NOT NULL THEN excluded.fulltext_source ELSE fulltext_source END,
                fulltext_fetched_at = CASE WHEN excluded.fulltext IS NOT NULL THEN datetime('now') ELSE fulltext_fetched_at END,
                summary = COALESCE(excluded.summary, summary),
                raw_json = COALESCE(excluded.raw_json, raw_json),
                updated_at = datetime('now')
            RETURNING id
            """,
            (source, provider_id, url_original, url_canonical, title, author,
             published_at, saved_at, fulltext, fulltext_html, fulltext_source, fulltext, summary, raw_json),
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

    def get_documents_without_embedding(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get documents that don't have embeddings yet.

        Returns documents with id, title, and text content for embedding.
        Text is built from: title + author + summary + fulltext (truncated).
        """
        cur = self.conn.execute(
            """
            SELECT d.id, d.title, d.author, d.summary, d.fulltext
            FROM documents d
            LEFT JOIN doc_embeddings e ON e.document_id = d.id
            WHERE e.document_id IS NULL
            ORDER BY d.id
            LIMIT ?
            """,
            (limit,),
        )
        docs = []
        for row in cur.fetchall():
            # Build text for embedding: title + author + summary + fulltext
            parts = []
            if row[1]:  # title
                parts.append(row[1])
            if row[2]:  # author
                parts.append(f"by {row[2]}")
            if row[3]:  # summary
                parts.append(row[3])
            if row[4]:  # fulltext
                parts.append(row[4])
            text = "\n\n".join(parts)
            docs.append({"id": row[0], "title": row[1], "text": text})
        return docs

    def save_embedding(self, document_id: int, embedding: bytes) -> None:
        """Save an embedding for a document.

        Args:
            document_id: The document ID
            embedding: Serialized embedding bytes (from serialize_f32)
        """
        # Delete existing embedding if any (for re-embedding)
        self.conn.execute(
            "DELETE FROM doc_embeddings WHERE document_id = ?",
            (document_id,),
        )
        self.conn.execute(
            "INSERT INTO doc_embeddings (embedding, document_id) VALUES (?, ?)",
            (embedding, document_id),
        )
        self.conn.commit()

    def get_embedding_stats(self) -> dict[str, int]:
        """Get embedding statistics."""
        cur = self.conn.execute("SELECT COUNT(*) FROM documents")
        total_docs = cur.fetchone()[0]
        cur = self.conn.execute("SELECT COUNT(*) FROM doc_embeddings")
        embedded_docs = cur.fetchone()[0]
        return {
            "total_documents": total_docs,
            "embedded_documents": embedded_docs,
            "pending": total_docs - embedded_docs,
        }

    def semantic_search(
        self, query_embedding: bytes, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search documents by semantic similarity.

        Args:
            query_embedding: Serialized embedding bytes (from serialize_f32)
            limit: Maximum number of results to return

        Returns:
            List of documents with id, title, author, url, saved_at, and distance
        """
        # sqlite-vec requires k=? syntax for KNN queries
        cur = self.conn.execute(
            """
            SELECT e.document_id, e.distance, d.title, d.author, d.url_original, d.saved_at
            FROM doc_embeddings e
            JOIN documents d ON d.id = e.document_id
            WHERE e.embedding MATCH ? AND k = ?
            ORDER BY e.distance
            """,
            (query_embedding, limit),
        )
        results = []
        for row in cur.fetchall():
            results.append(
                {
                    "id": row[0],
                    "distance": row[1],
                    "title": row[2],
                    "author": row[3],
                    "url": row[4],
                    "saved_at": row[5],
                }
            )
        return results

    # ==================== Chunk Methods ====================

    def save_chunks(
        self, document_id: int, chunks: list[dict[str, Any]]
    ) -> list[int]:
        """Save chunks for a document.

        Args:
            document_id: The document ID
            chunks: List of chunk dicts with keys:
                - chunk_index: int
                - chunk_text: str
                - char_start: int
                - char_end: int
                - token_count: int (optional)

        Returns:
            List of chunk IDs
        """
        # Delete existing chunks for this document (re-chunking)
        self.conn.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )

        chunk_ids = []
        for chunk in chunks:
            cur = self.conn.execute(
                """
                INSERT INTO document_chunks (document_id, chunk_index, chunk_text, char_start, char_end, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    document_id,
                    chunk["chunk_index"],
                    chunk["chunk_text"],
                    chunk["char_start"],
                    chunk["char_end"],
                    chunk.get("token_count"),
                ),
            )
            chunk_ids.append(cur.fetchone()[0])

        self.conn.commit()
        return chunk_ids

    def get_chunks_for_document(self, document_id: int) -> list[dict[str, Any]]:
        """Get all chunks for a document."""
        cur = self.conn.execute(
            """
            SELECT id, chunk_index, chunk_text, char_start, char_end, token_count
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY chunk_index
            """,
            (document_id,),
        )
        return [
            {
                "id": row[0],
                "chunk_index": row[1],
                "chunk_text": row[2],
                "char_start": row[3],
                "char_end": row[4],
                "token_count": row[5],
            }
            for row in cur.fetchall()
        ]

    def get_chunk_context(
        self, chunk_id: int, context_chunks: int = 2
    ) -> dict[str, Any]:
        """Get a chunk with surrounding context.

        Args:
            chunk_id: The chunk ID
            context_chunks: Number of chunks before/after to include

        Returns:
            Dict with chunk info and context_before/context_after
        """
        # Get the chunk and its document_id
        cur = self.conn.execute(
            """
            SELECT id, document_id, chunk_index, chunk_text, char_start, char_end
            FROM document_chunks WHERE id = ?
            """,
            (chunk_id,),
        )
        row = cur.fetchone()
        if not row:
            return {}

        chunk = {
            "id": row[0],
            "document_id": row[1],
            "chunk_index": row[2],
            "chunk_text": row[3],
            "char_start": row[4],
            "char_end": row[5],
        }

        # Get surrounding chunks
        cur = self.conn.execute(
            """
            SELECT chunk_index, chunk_text
            FROM document_chunks
            WHERE document_id = ? AND chunk_index BETWEEN ? AND ?
            ORDER BY chunk_index
            """,
            (
                chunk["document_id"],
                chunk["chunk_index"] - context_chunks,
                chunk["chunk_index"] + context_chunks,
            ),
        )

        context_before = []
        context_after = []
        for ctx_row in cur.fetchall():
            if ctx_row[0] < chunk["chunk_index"]:
                context_before.append(ctx_row[1])
            elif ctx_row[0] > chunk["chunk_index"]:
                context_after.append(ctx_row[1])

        chunk["context_before"] = "\n".join(context_before)
        chunk["context_after"] = "\n".join(context_after)

        return chunk

    # ==================== New Embeddings Methods ====================

    def save_embedding_v2(
        self,
        *,
        embedding: bytes,
        dimensions: int,
        provider: str,
        model: str,
        document_id: int | None = None,
        chunk_id: int | None = None,
    ) -> int:
        """Save an embedding with provider info.

        Args:
            embedding: Serialized embedding bytes (from serialize_f32)
            dimensions: Vector dimensions (768, 1024, 1536, 3072)
            provider: Provider name ('openai', 'ollama')
            model: Model ID ('text-embedding-3-small', etc.)
            document_id: Document ID (for document-level embedding)
            chunk_id: Chunk ID (for chunk-level embedding)

        Returns:
            Embedding ID
        """
        if document_id is None and chunk_id is None:
            raise ValueError("Either document_id or chunk_id must be provided")

        # Insert into embeddings table
        cur = self.conn.execute(
            """
            INSERT INTO embeddings (document_id, chunk_id, provider, model, embedding, dimensions)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (document_id, chunk_id, provider, model, embedding, dimensions),
        )
        embedding_id = cur.fetchone()[0]

        # Insert into vec0 table for KNN search
        vec_table = f"embeddings_{dimensions}"
        self.conn.execute(
            f"INSERT INTO {vec_table} (embedding, embedding_id) VALUES (?, ?)",
            (embedding, embedding_id),
        )

        self.conn.commit()
        return embedding_id

    def save_embeddings_batch(
        self,
        embeddings_data: list[dict],
        dimensions: int,
        provider: str,
        model: str,
    ) -> int:
        """Save multiple embeddings in a single transaction (batch operation).

        This method saves all embeddings atomically, avoiding SQLite concurrency
        issues that can occur when saving embeddings one-by-one in async contexts.

        Args:
            embeddings_data: List of dicts with keys:
                - embedding: bytes (serialized embedding)
                - chunk_id: int (optional)
                - document_id: int (optional)
            dimensions: Vector dimensions (768, 1024, 1536, 3072)
            provider: Provider name ('openai', 'ollama')
            model: Model ID

        Returns:
            Number of embeddings saved
        """
        if not embeddings_data:
            return 0

        vec_table = f"embeddings_{dimensions}"
        count = 0

        for data in embeddings_data:
            embedding = data["embedding"]
            chunk_id = data.get("chunk_id")
            document_id = data.get("document_id")

            if document_id is None and chunk_id is None:
                continue

            # Use lastrowid instead of RETURNING to avoid cursor issues
            cur = self.conn.execute(
                """
                INSERT INTO embeddings (document_id, chunk_id, provider, model, embedding, dimensions)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_id, chunk_id, provider, model, embedding, dimensions),
            )
            embedding_id = cur.lastrowid

            self.conn.execute(
                f"INSERT INTO {vec_table} (embedding, embedding_id) VALUES (?, ?)",
                (embedding, embedding_id),
            )
            count += 1

        # Single commit for entire batch
        self.conn.commit()
        return count

    def semantic_search_v2(
        self,
        query_embedding: bytes,
        dimensions: int,
        limit: int = 10,
        search_chunks: bool = False,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search documents or chunks by semantic similarity.

        Args:
            query_embedding: Serialized embedding bytes
            dimensions: Vector dimensions (must match the embedding model)
            limit: Maximum results
            search_chunks: If True, search chunk embeddings; otherwise document embeddings
            provider: Optional filter by provider
            model: Optional filter by model

        Returns:
            List of results with distance and metadata
        """
        vec_table = f"embeddings_{dimensions}"

        if search_chunks:
            # Search in chunks
            query = f"""
                SELECT v.embedding_id, v.distance,
                       e.chunk_id, c.chunk_text, c.char_start, c.char_end, c.document_id,
                       d.title, d.author, d.url_original
                FROM {vec_table} v
                JOIN embeddings e ON e.id = v.embedding_id
                JOIN document_chunks c ON c.id = e.chunk_id
                JOIN documents d ON d.id = c.document_id
                WHERE v.embedding MATCH ? AND k = ?
                  AND e.chunk_id IS NOT NULL
            """
            params: list[Any] = [query_embedding, limit]

            if provider:
                query += " AND e.provider = ?"
                params.append(provider)
            if model:
                query += " AND e.model = ?"
                params.append(model)

            query += " ORDER BY v.distance"
            cur = self.conn.execute(query, params)

            results = []
            for row in cur.fetchall():
                results.append({
                    "embedding_id": row[0],
                    "distance": row[1],
                    "chunk_id": row[2],
                    "chunk_text": row[3],
                    "char_start": row[4],
                    "char_end": row[5],
                    "document_id": row[6],
                    "title": row[7],
                    "author": row[8],
                    "url": row[9],
                })
            return results

        else:
            # Search in documents
            query = f"""
                SELECT v.embedding_id, v.distance,
                       e.document_id, d.title, d.author, d.url_original, d.saved_at
                FROM {vec_table} v
                JOIN embeddings e ON e.id = v.embedding_id
                JOIN documents d ON d.id = e.document_id
                WHERE v.embedding MATCH ? AND k = ?
                  AND e.document_id IS NOT NULL
            """
            params = [query_embedding, limit]

            if provider:
                query += " AND e.provider = ?"
                params.append(provider)
            if model:
                query += " AND e.model = ?"
                params.append(model)

            query += " ORDER BY v.distance"
            cur = self.conn.execute(query, params)

            results = []
            for row in cur.fetchall():
                results.append({
                    "embedding_id": row[0],
                    "distance": row[1],
                    "id": row[2],
                    "title": row[3],
                    "author": row[4],
                    "url": row[5],
                    "saved_at": row[6],
                })
            return results

    def get_documents_without_embedding_v2(
        self, provider: str, model: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get documents that don't have embeddings for a specific provider/model.

        Returns documents with id, title, and text content for embedding.
        """
        cur = self.conn.execute(
            """
            SELECT d.id, d.title, d.author, d.summary, d.fulltext
            FROM documents d
            LEFT JOIN embeddings e ON e.document_id = d.id
                AND e.provider = ? AND e.model = ?
            WHERE e.id IS NULL
            ORDER BY d.id
            LIMIT ?
            """,
            (provider, model, limit),
        )
        docs = []
        for row in cur.fetchall():
            parts = []
            if row[1]:  # title
                parts.append(row[1])
            if row[2]:  # author
                parts.append(f"by {row[2]}")
            if row[3]:  # summary
                parts.append(row[3])
            if row[4]:  # fulltext
                parts.append(row[4])
            text = "\n\n".join(parts)
            docs.append({"id": row[0], "title": row[1], "text": text})
        return docs

    def get_embedding_stats_v2(self) -> dict[str, Any]:
        """Get detailed embedding statistics by provider/model."""
        cur = self.conn.execute("SELECT COUNT(*) FROM documents")
        total_docs = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(*) FROM document_chunks")
        total_chunks = cur.fetchone()[0]

        # Get stats by provider/model
        cur = self.conn.execute(
            """
            SELECT provider, model,
                   SUM(CASE WHEN document_id IS NOT NULL THEN 1 ELSE 0 END) as doc_count,
                   SUM(CASE WHEN chunk_id IS NOT NULL THEN 1 ELSE 0 END) as chunk_count
            FROM embeddings
            GROUP BY provider, model
            """
        )
        by_provider = []
        for row in cur.fetchall():
            by_provider.append({
                "provider": row[0],
                "model": row[1],
                "document_embeddings": row[2],
                "chunk_embeddings": row[3],
            })

        # Legacy stats (doc_embeddings table)
        cur = self.conn.execute("SELECT COUNT(*) FROM doc_embeddings")
        legacy_count = cur.fetchone()[0]

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "by_provider": by_provider,
            "legacy_embeddings": legacy_count,
        }

    def get_chunks_for_embedding(
        self,
        limit: int = 200,
        cursor_chunk_id: int | None = None,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
    ) -> list[dict[str, Any]]:
        """Get chunks without embeddings (cursor-based for resume).

        Returns chunks that don't have an embedding for the given provider/model.
        Results are ordered by chunk id for consistent cursor-based pagination.
        Uses NOT EXISTS (faster than LEFT JOIN for this pattern).
        """
        cursor_id = cursor_chunk_id or 0
        cur = self.conn.execute(
            """
            SELECT c.id, c.document_id, c.chunk_text, c.token_count
            FROM document_chunks c
            WHERE c.id > ?
              AND NOT EXISTS (
                  SELECT 1 FROM embeddings e
                  WHERE e.chunk_id = c.id
                    AND e.provider = ?
                    AND e.model = ?
              )
            ORDER BY c.id
            LIMIT ?
            """,
            (cursor_id, provider, model, limit),
        )
        return [
            {
                "id": row[0],
                "document_id": row[1],
                "chunk_text": row[2],
                "token_count": row[3] or 0,
            }
            for row in cur.fetchall()
        ]

    def count_chunks_for_embedding(
        self,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
    ) -> dict[str, int]:
        """Get stats for embedding generation.

        Returns:
            total_chunks: All chunks in DB
            embedded_chunks: Chunks with embedding for this provider/model
            pending_chunks: Chunks without embedding (always >= 0)
            orphaned_embeddings: Embeddings for deleted chunks (cleanup candidate)
        """
        cur = self.conn.execute("SELECT COUNT(*) FROM document_chunks")
        total = cur.fetchone()[0]

        # Count chunks that HAVE an embedding (only existing chunks)
        cur = self.conn.execute(
            """
            SELECT COUNT(DISTINCT c.id)
            FROM document_chunks c
            JOIN embeddings e ON e.chunk_id = c.id
            WHERE e.provider = ? AND e.model = ?
            """,
            (provider, model),
        )
        embedded = cur.fetchone()[0]

        # Count orphaned embeddings (embeddings for deleted chunks)
        cur = self.conn.execute(
            """
            SELECT COUNT(DISTINCT e.chunk_id)
            FROM embeddings e
            LEFT JOIN document_chunks c ON c.id = e.chunk_id
            WHERE c.id IS NULL
              AND e.provider = ? AND e.model = ?
            """,
            (provider, model),
        )
        orphaned = cur.fetchone()[0]

        return {
            "total_chunks": total,
            "embedded_chunks": embedded,
            "pending_chunks": total - embedded,  # Now always >= 0
            "orphaned_embeddings": orphaned,
        }

    # ==================== Usage Tracking ====================

    def log_api_usage(
        self,
        *,
        provider: str,
        model: str,
        operation: str,
        tokens_input: int,
        cost_usd: float,
        tokens_output: int = 0,
        latency_ms: int | None = None,
        success: bool = True,
        error_message: str | None = None,
        metadata: str | None = None,
    ) -> int:
        """Log an API call for usage tracking.

        Returns the usage record ID.
        """
        cur = self.conn.execute(
            """
            INSERT INTO api_usage (
                provider, model, operation, tokens_input, tokens_output,
                cost_usd, latency_ms, success, error_message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                model,
                operation,
                tokens_input,
                tokens_output,
                cost_usd,
                latency_ms,
                1 if success else 0,
                error_message,
                metadata,
            ),
        )
        usage_id = cur.lastrowid
        self.conn.commit()
        return usage_id

    def semantic_search_with_chunks(
        self,
        query_embedding: bytes,
        dimensions: int = 1536,
        limit: int = 10,
        include_context: bool = True,
    ) -> list[dict[str, Any]]:
        """Search with chunk-level results and context for citations.

        Uses the new embeddings table if chunk embeddings exist,
        otherwise falls back to document-level search.

        Args:
            query_embedding: Serialized embedding bytes
            dimensions: Vector dimensions (must match model)
            limit: Maximum results
            include_context: Include surrounding chunks for context

        Returns:
            List of results with chunk_text, position data, and context
        """
        # Check if we have chunk embeddings
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM embeddings WHERE chunk_id IS NOT NULL"
        )
        chunk_count = cur.fetchone()[0]

        if chunk_count == 0:
            # Fall back to document-level search
            return self.semantic_search(query_embedding, limit)

        # Search in chunk embeddings
        vec_table = f"embeddings_{dimensions}"

        try:
            cur = self.conn.execute(
                f"""
                SELECT v.embedding_id, v.distance,
                       e.chunk_id, c.chunk_text, c.char_start, c.char_end,
                       c.chunk_index, c.document_id,
                       d.title, d.author, d.url_original, d.saved_at
                FROM {vec_table} v
                JOIN embeddings e ON e.id = v.embedding_id
                JOIN document_chunks c ON c.id = e.chunk_id
                JOIN documents d ON d.id = c.document_id
                WHERE v.embedding MATCH ? AND k = ?
                  AND e.chunk_id IS NOT NULL
                ORDER BY v.distance
                """,
                (query_embedding, limit),
            )

            results = []
            for row in cur.fetchall():
                result = {
                    "id": row[7],  # document_id
                    "distance": row[1],
                    "chunk_id": row[2],
                    "chunk_text": row[3],
                    "char_start": row[4],
                    "char_end": row[5],
                    "chunk_index": row[6],
                    "title": row[8],
                    "author": row[9],
                    "url": row[10],
                    "saved_at": row[11],
                }

                # Get context if requested
                if include_context:
                    context = self.get_chunk_context(row[2], context_chunks=1)
                    result["context_before"] = context.get("context_before", "")
                    result["context_after"] = context.get("context_after", "")

                results.append(result)

            return results

        except Exception:
            # Fallback if vec table doesn't exist or other error
            return self.semantic_search(query_embedding, limit)

    # ==================== Fetch Job Methods ====================

    def get_documents_for_fetch(
        self, limit: int = 100, cursor_doc_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Get documents that need fulltext fetching.

        Returns documents with URL but no fulltext yet.
        """
        query = """
            SELECT d.id, d.url_original, d.title
            FROM documents d
            LEFT JOIN fetch_failures f ON f.document_id = d.id
            WHERE d.url_original IS NOT NULL
              AND d.url_original != ''
              AND (d.fulltext IS NULL OR d.fulltext = '')
              AND f.id IS NULL  -- No previous failure
        """
        params: list[Any] = []

        if cursor_doc_id is not None:
            query += " AND d.id > ?"
            params.append(cursor_doc_id)

        query += " ORDER BY d.id LIMIT ?"
        params.append(limit)

        cur = self.conn.execute(query, params)
        return [
            {"id": row[0], "url": row[1], "title": row[2]}
            for row in cur.fetchall()
        ]

    def count_documents_for_fetch(self) -> dict[str, int]:
        """Count documents for fetch statistics."""
        cur = self.conn.execute("SELECT COUNT(*) FROM documents")
        total = cur.fetchone()[0]

        cur = self.conn.execute(
            """SELECT COUNT(*) FROM documents
               WHERE url_original IS NOT NULL AND url_original != ''"""
        )
        with_url = cur.fetchone()[0]

        cur = self.conn.execute(
            """SELECT COUNT(*) FROM documents
               WHERE fulltext IS NOT NULL AND fulltext != ''"""
        )
        with_fulltext = cur.fetchone()[0]

        cur = self.conn.execute("SELECT COUNT(*) FROM fetch_failures")
        failed = cur.fetchone()[0]

        # Pending = with URL but no fulltext and no failure
        cur = self.conn.execute(
            """SELECT COUNT(*) FROM documents d
               LEFT JOIN fetch_failures f ON f.document_id = d.id
               WHERE d.url_original IS NOT NULL AND d.url_original != ''
                 AND (d.fulltext IS NULL OR d.fulltext = '')
                 AND f.id IS NULL"""
        )
        pending = cur.fetchone()[0]

        # Documents with fulltext but no chunks (ready for chunking)
        cur = self.conn.execute(
            """SELECT COUNT(*) FROM documents d
               LEFT JOIN document_chunks c ON c.document_id = d.id
               WHERE d.fulltext IS NOT NULL AND d.fulltext != ''
                 AND c.id IS NULL"""
        )
        without_chunks = cur.fetchone()[0]

        return {
            "total": total,
            "with_url": with_url,
            "with_fulltext": with_fulltext,
            "failed": failed,
            "pending": pending,
            "without_chunks": without_chunks,
        }

    def save_fulltext(
        self,
        document_id: int,
        fulltext: str,
        source: str = "trafilatura",
    ) -> None:
        """Save fetched fulltext for a document."""
        self.conn.execute(
            """UPDATE documents SET
                fulltext = ?,
                fulltext_fetched_at = datetime('now'),
                fulltext_source = ?,
                updated_at = datetime('now')
               WHERE id = ?""",
            (fulltext, source, document_id),
        )
        self.conn.commit()

    def save_fetch_failure(
        self,
        *,
        document_id: int,
        url: str,
        error_type: str,
        error_message: str | None = None,
        http_status: int | None = None,
        job_id: str | None = None,
    ) -> None:
        """Save a fetch failure for a document."""
        self.conn.execute(
            """INSERT INTO fetch_failures
               (document_id, job_id, url, error_type, error_message, http_status)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(document_id) DO UPDATE SET
                 job_id = excluded.job_id,
                 error_type = excluded.error_type,
                 error_message = excluded.error_message,
                 http_status = excluded.http_status,
                 retry_count = retry_count + 1,
                 last_attempt = datetime('now')""",
            (document_id, job_id, url, error_type, error_message, http_status),
        )
        self.conn.commit()

    def get_fetch_failures(
        self, error_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get fetch failures, optionally filtered by error type."""
        query = """
            SELECT f.id, f.document_id, d.title, f.url, f.error_type,
                   f.error_message, f.http_status, f.retry_count, f.last_attempt
            FROM fetch_failures f
            JOIN documents d ON d.id = f.document_id
        """
        params: list[Any] = []

        if error_type:
            query += " WHERE f.error_type = ?"
            params.append(error_type)

        query += " ORDER BY f.last_attempt DESC LIMIT ?"
        params.append(limit)

        cur = self.conn.execute(query, params)
        return [
            {
                "id": row[0],
                "document_id": row[1],
                "title": row[2],
                "url": row[3],
                "error_type": row[4],
                "error_message": row[5],
                "http_status": row[6],
                "retry_count": row[7],
                "last_attempt": row[8],
            }
            for row in cur.fetchall()
        ]

    def get_failure_summary(self) -> dict[str, int]:
        """Get failure counts by error type."""
        cur = self.conn.execute(
            """SELECT error_type, COUNT(*) FROM fetch_failures GROUP BY error_type"""
        )
        return {row[0]: row[1] for row in cur.fetchall()}

    def clear_retryable_failures(self) -> int:
        """Clear failures that can be retried (timeout, http_5xx).

        Returns number of cleared failures.
        """
        cur = self.conn.execute(
            """DELETE FROM fetch_failures
               WHERE error_type IN ('timeout', 'http_5xx')
               RETURNING id"""
        )
        count = len(cur.fetchall())
        self.conn.commit()
        return count

    def get_usage_stats(self, period: str = "today") -> dict[str, Any]:
        """Get usage statistics for a time period.

        Args:
            period: 'today', 'week', 'month', or 'all'
        """
        date_filter = ""
        if period == "today":
            date_filter = "WHERE date(timestamp) = date('now')"
        elif period == "week":
            date_filter = "WHERE timestamp >= datetime('now', '-7 days')"
        elif period == "month":
            date_filter = "WHERE timestamp >= datetime('now', '-30 days')"

        cur = self.conn.execute(
            f"""
            SELECT
                SUM(cost_usd) as total_cost,
                SUM(tokens_input) as total_tokens_input,
                SUM(tokens_output) as total_tokens_output,
                COUNT(*) as total_requests,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
            FROM api_usage
            {date_filter}
            """
        )
        row = cur.fetchone()

        # By provider
        cur = self.conn.execute(
            f"""
            SELECT provider,
                   SUM(cost_usd) as cost,
                   SUM(tokens_input) as tokens,
                   COUNT(*) as requests,
                   AVG(latency_ms) as avg_latency
            FROM api_usage
            {date_filter}
            GROUP BY provider
            """
        )
        by_provider = {r[0]: {"cost": r[1], "tokens": r[2], "requests": r[3], "avg_latency": r[4]} for r in cur.fetchall()}

        # By operation
        cur = self.conn.execute(
            f"""
            SELECT operation,
                   SUM(cost_usd) as cost,
                   COUNT(*) as requests
            FROM api_usage
            {date_filter}
            GROUP BY operation
            """
        )
        by_operation = {r[0]: {"cost": r[1], "requests": r[2]} for r in cur.fetchall()}

        return {
            "period": period,
            "total_cost_usd": row[0] or 0,
            "total_tokens_input": row[1] or 0,
            "total_tokens_output": row[2] or 0,
            "total_requests": row[3] or 0,
            "avg_latency_ms": round(row[4] or 0),
            "error_count": row[5] or 0,
            "by_provider": by_provider,
            "by_operation": by_operation,
        }

    # ==================== App Settings (Theme etc.) ====================

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a setting value by key."""
        cur = self.conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,)
        )
        row = cur.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value (upsert)."""
        self.conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now')
            """,
            (key, value)
        )
        self.conn.commit()

    def get_theme(self) -> dict[str, str]:
        """Get theme settings with defaults."""
        return {
            "primary": self.get_setting("theme_primary", "#3b82f6"),
        }

    def set_theme(self, primary: str) -> None:
        """Update theme settings."""
        self.set_setting("theme_primary", primary)


_db: DB | None = None


def init_db() -> None:
    global _db
    from app.core.import_job import init_import_store
    from app.core.fetch_job import init_fetch_store
    from app.core.embed_job_v2 import init_embed_store

    s = Settings.from_env()
    os.makedirs(os.path.dirname(s.db_path), exist_ok=True)

    conn = sqlite3.connect(s.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # sqlite-vec must be loaded into this connection
    sqlite_vec.load(conn)

    _db = DB(conn=conn)
    _db.init()

    # Initialize job stores with same connection
    init_import_store(conn)
    init_fetch_store(conn)
    init_embed_store(conn)


def get_db() -> DB:
    assert _db is not None, "DB not initialized"
    return _db
