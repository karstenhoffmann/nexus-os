# Digest 2.0 - Phase A: Source Transparency

**Technical Specification v1.1**
**Date:** December 2025
**Status:** Draft - Updated with Database Scalability Fixes

---

## Executive Summary

Phase A establishes the **foundation for source transparency** - the ability to trace every digest insight back to its original source chunks. This is the prerequisite for all subsequent Digest 2.0 features (curation, draft bridge, lens system).

**Core Deliverable:** Every topic and insight in a digest can be drilled down to see the exact chunks (with document context) that informed it.

---

## Phase A-0: Database Scalability Prerequisites (NEW)

**Status:** Must complete before Phase A implementation

### Critical Issue: N+1 Semantic Search Pattern

**Location:** `app/core/storage.py:1062-1077`

**Problem:** Current semantic search executes 250 individual queries per request:
```python
# Current (BROKEN at scale)
for result in knn_results:  # 250 iterations
    cur = self.conn.execute(
        "SELECT ... FROM embeddings e JOIN documents d ... WHERE e.id = ?",
        (result["embedding_id"],)
    )
```

**Impact:** At 500k chunks, each search would take 10-30 seconds instead of <500ms.

**Fix Required:**
```python
# Target (single query)
embedding_ids = [r["embedding_id"] for r in knn_results]
placeholders = ",".join("?" * len(embedding_ids))
cur = self.conn.execute(f"""
    SELECT e.id, e.chunk_id, c.chunk_text, d.id, d.title, d.author, d.url_original
    FROM embeddings e
    JOIN document_chunks c ON c.id = e.chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE e.id IN ({placeholders})
""", embedding_ids)
```

### Missing Index: documents.saved_at

**Location:** Schema definition

**Problem:** All date-range queries do full table scans.

**Fix Required:**
```sql
CREATE INDEX IF NOT EXISTS idx_documents_saved_at ON documents(saved_at DESC);
```

### Missing Column: documents.reader_url

**Problem:** Cannot implement "Open in Reader" action without this.

**Fix Required:**
```sql
ALTER TABLE documents ADD COLUMN reader_url TEXT;
```

### Dead Code: chunks_fts

**Location:** `storage.py:217-221`

**Problem:** FTS5 table defined but never populated.

**Decision Required:** Remove dead code OR implement chunk FTS.

### Phase A-0 Implementation Order

```
1. Add saved_at index (5 min)
2. Add reader_url column (10 min)
3. Fix N+1 semantic search pattern (2-4 hours)
4. Remove chunks_fts dead code (10 min)
5. Verify with manual testing
```

---

---

## 1. Current State Analysis

### 1.1 Data Model (What Exists)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT STATE                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  generated_digests                                               │
│  ├── id, name, title                                            │
│  ├── topics_json (TEXT) ◄── ALL topics as JSON blob             │
│  ├── highlights_json (TEXT) ◄── ALL highlights as JSON blob     │
│  └── (metadata: dates, costs, tokens)                           │
│                                                                  │
│  digest_topics (EXISTS BUT UNUSED)                               │
│  ├── id, digest_id, topic_index                                 │
│  ├── topic_name, summary, chunk_count                           │
│  └── (no chunk_ids stored!)                                     │
│                                                                  │
│  digest_citations (EXISTS BUT UNUSED)                            │
│  ├── id, digest_id, topic_id                                    │
│  ├── chunk_id, document_id                                      │
│  ├── citation_type, excerpt                                     │
│  └── (never populated!)                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Pipeline Flow (What Happens Now)

```
FETCH ──► CLUSTER ──► SUMMARIZE ──► COMPILE
  │          │            │            │
  │          │            │            ▼
  │          │            │     db.save_generated_digest()
  │          │            │         ├── topics_json = JSON blob
  │          │            │         └── highlights_json = JSON blob
  │          │            │
  │          │            │     ❌ digest_topics NOT populated
  │          │            │     ❌ digest_citations NOT populated
  │          │            │
  │          ▼            │
  │    ClusteringResult   │
  │    └── clusters[]     │
  │        └── chunk_ids  │◄─── chunk IDs known but LOST
  │                       │
  ▼                       │
chunks[] ─────────────────┘
  └── id, document_id, chunk_text, title, author, url
      (all metadata available but not persisted to citations)
```

### 1.3 Problems with Current State

| Problem | Impact | Location |
|---------|--------|----------|
| Topics stored as JSON blob | Can't query individual topics efficiently | `storage.py:299` |
| Citations table never populated | Zero source transparency | `digest_pipeline.py:363` |
| Chunk metadata lost after clustering | Can't show document context in UI | `digest_clustering.py:273` |
| Highlights detached from sources | Can't trace "key point" → chunk | `digest_pipeline.py:321` |
| No drill-down API endpoints | Frontend can't request sources | `main.py` |

---

## 2. Target State Design

### 2.1 Data Model (After Phase A)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TARGET STATE                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  generated_digests                                               │
│  ├── id, name, title                                            │
│  ├── topics_json (DEPRECATED - kept for backward compat)        │
│  ├── highlights_json (DEPRECATED - kept for backward compat)    │
│  └── (metadata: dates, costs, tokens)                           │
│                                                                  │
│  digest_topics (PRIMARY SOURCE OF TRUTH)                         │
│  ├── id, digest_id, topic_index                                 │
│  ├── topic_name, summary                                        │
│  ├── key_points_json (NEW) ◄── structured key points            │
│  └── chunk_count                                                │
│           │                                                      │
│           │ 1:N                                                  │
│           ▼                                                      │
│  digest_citations (FULLY POPULATED)                              │
│  ├── id, digest_id, topic_id                                    │
│  ├── chunk_id ──► document_chunks.id                            │
│  ├── document_id ──► documents.id                               │
│  ├── citation_type ('topic_source' | 'highlight_source')        │
│  └── excerpt (chunk text snippet)                               │
│           │                                                      │
│           │ JOIN                                                 │
│           ▼                                                      │
│  documents (EXISTING - read via JOIN)                            │
│  ├── title, author                                              │
│  ├── url_original ◄── for [Original ↗] action                   │
│  └── reader_url (NEW) ◄── for [Open in Reader] action           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Pipeline Flow (After Phase A)

```
FETCH ──► CLUSTER ──► SUMMARIZE ──► COMPILE
  │          │            │            │
  │          │            │            ▼
  │          │            │     1. db.save_generated_digest()
  │          │            │           └── (metadata only)
  │          │            │
  │          │            │     2. For each cluster:
  │          │            │        topic_id = db.save_digest_topic()
  │          │            │
  │          │            │     3. For each chunk in cluster:
  │          │            │        db.save_digest_citation(
  │          │            │          topic_id, chunk_id, document_id
  │          │            │        )
  │          │            │
  │          ▼            │
  │    ClusteringResult   │
  │    └── clusters[]     │
  │        └── chunk_ids ─┼──► persisted to digest_citations
  │                       │
  ▼                       │
chunks[] ─────────────────┘
  └── chunk_to_doc mapping passed to COMPILE
```

### 2.3 API Endpoints (New)

```
# Existing (unchanged)
GET  /api/digest/{digest_id}           → Digest with topics (from tables)

# New endpoints for drill-down
GET  /api/digest/{digest_id}/topics/{topic_id}/sources
     → Returns: list of chunks with document context
     → Used by: "View sources" UI expansion

# Response shape for /sources:
{
  "topic_id": 42,
  "topic_name": "AI Model Efficiency",
  "source_count": 8,
  "sources": [
    {
      "citation_id": 101,
      "chunk_id": 5432,
      "document_id": 87,
      "excerpt": "domain-specific fine-tuning on a 7B model...",
      "chunk_index": 47,
      "document": {
        "title": "The End of Scaling Laws?",
        "author": "AI Research Weekly",
        "url_original": "https://example.com/article",
        "reader_url": "https://readwise.io/read/...",
        "saved_at": "2025-12-18T10:30:00Z"
      }
    },
    ...
  ]
}
```

---

## 3. Implementation Specification

### 3.1 Phase A-1: Wire Citations in COMPILE

**File:** `app/core/digest_pipeline.py`

#### Change 1: Pass chunk mapping to COMPILE

**Location:** `run_digest_pipeline()` function, around line 140

**Current:**
```python
digest_id = await _compile_phase(
    job, db, clustering_result, title, overall_summary, highlights, store
)
```

**Target:**
```python
# Build chunk_id → (document_id, chunk_text) mapping for citations
chunk_metadata = {
    c["id"]: {
        "document_id": c["document_id"],
        "excerpt": c["chunk_text"][:500],  # First 500 chars as excerpt
    }
    for c in chunks
}

digest_id = await _compile_phase(
    job, db, clustering_result, title, overall_summary, highlights, store,
    chunk_metadata=chunk_metadata,
)
```

#### Change 2: Update COMPILE phase signature and implementation

**Location:** `_compile_phase()` function, lines 335-387

**Current signature:**
```python
async def _compile_phase(
    job: DigestJob,
    db: DB,
    clustering_result: ClusteringResult,
    title: str,
    overall_summary: str,
    highlights: list[str],
    store: Any,
) -> int:
```

**Target signature:**
```python
async def _compile_phase(
    job: DigestJob,
    db: DB,
    clustering_result: ClusteringResult,
    title: str,
    overall_summary: str,
    highlights: list[str],
    store: Any,
    *,
    chunk_metadata: dict[int, dict] | None = None,
) -> int:
```

**Target implementation (replace lines 363-386):**

```python
    # Save to database
    digest_id = db.save_generated_digest(
        name=name,
        title=title if title else None,
        time_range_days=job.days,
        date_from=date_from_str,
        date_to=date_to_str,
        strategy=job.strategy,
        model_id=job.model,
        summary_text=overall_summary,
        topics_json=topics_json,  # Keep for backward compat (deprecated)
        highlights_json=highlights_json,
        docs_analyzed=job.docs_found,
        chunks_analyzed=job.chunks_found,
        tokens_input=job.tokens_input,
        tokens_output=job.tokens_output,
        cost_usd=job.cost_usd,
    )

    # NEW: Populate normalized tables for source transparency
    if chunk_metadata:
        for cluster in clustering_result.clusters:
            # Save topic to digest_topics table
            topic_id = db.save_digest_topic(
                digest_id=digest_id,
                topic_index=cluster.topic_index,
                topic_name=cluster.topic_name,
                summary=cluster.summary,
                chunk_count=cluster.chunk_count,
                key_points_json=json.dumps(cluster.key_points, ensure_ascii=False)
                    if cluster.key_points else None,
            )

            # Save citation for each chunk in this topic
            for chunk_id in cluster.chunk_ids:
                meta = chunk_metadata.get(chunk_id, {})
                db.save_digest_citation(
                    digest_id=digest_id,
                    topic_id=topic_id,
                    chunk_id=chunk_id,
                    document_id=meta.get("document_id"),
                    citation_type="topic_source",
                    excerpt=meta.get("excerpt"),
                )

    logger.info(
        f"Saved digest {digest_id}: '{title or name}', "
        f"{len(clustering_result.clusters)} topics, "
        f"{sum(c.chunk_count for c in clustering_result.clusters)} citations, "
        f"cost: ${job.cost_usd:.4f}"
    )

    return digest_id
```

---

### 3.2 Phase A-2: Update Data Retrieval

**File:** `app/core/storage.py`

#### Change 1: Add key_points_json column to digest_topics

**Location:** Schema definition, around line 311-318

**Add migration in `_ensure_digest_tables()`:**

```python
# After existing digest_topics migration
cur = conn.execute("PRAGMA table_info(digest_topics)")
existing_cols = {row[1] for row in cur.fetchall()}
if "key_points_json" not in existing_cols:
    conn.execute("ALTER TABLE digest_topics ADD COLUMN key_points_json TEXT")
    conn.commit()
```

#### Change 2: Update save_digest_topic to accept key_points_json

**Location:** `save_digest_topic()` method, around line 3029

**Current:**
```python
def save_digest_topic(
    self,
    *,
    digest_id: int,
    topic_index: int,
    topic_name: str,
    summary: str,
    chunk_count: int | None = None,
) -> int:
```

**Target:**
```python
def save_digest_topic(
    self,
    *,
    digest_id: int,
    topic_index: int,
    topic_name: str,
    summary: str,
    chunk_count: int | None = None,
    key_points_json: str | None = None,
) -> int:
    """Save a topic for a generated digest. Returns topic id."""
    cur = self.conn.execute(
        """
        INSERT INTO digest_topics (digest_id, topic_index, topic_name, summary, chunk_count, key_points_json)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (digest_id, topic_index, topic_name, summary, chunk_count, key_points_json),
    )
    topic_id = cur.fetchone()[0]
    self.conn.commit()
    return topic_id
```

#### Change 3: Add method to get topic sources with document context

**Location:** After `get_digest_citations()` method, around line 3113

**New method:**

```python
def get_topic_sources(
    self,
    digest_id: int,
    topic_id: int,
) -> dict[str, Any]:
    """Get sources for a specific topic with full document context.

    Returns topic info plus list of sources with document metadata.
    Used for source drill-down UI.
    """
    # Get topic info
    cur = self.conn.execute(
        """
        SELECT id, topic_index, topic_name, summary, chunk_count, key_points_json
        FROM digest_topics
        WHERE digest_id = ? AND id = ?
        """,
        (digest_id, topic_id),
    )
    topic_row = cur.fetchone()
    if not topic_row:
        return None

    # Get citations with document context
    cur = self.conn.execute(
        """
        SELECT
            c.id as citation_id,
            c.chunk_id,
            c.document_id,
            c.citation_type,
            c.excerpt,
            ch.chunk_index,
            ch.chunk_text,
            d.title as doc_title,
            d.author as doc_author,
            d.url_original,
            d.saved_at,
            d.category
        FROM digest_citations c
        LEFT JOIN document_chunks ch ON ch.id = c.chunk_id
        LEFT JOIN documents d ON d.id = c.document_id
        WHERE c.digest_id = ? AND c.topic_id = ?
        ORDER BY d.saved_at DESC, ch.chunk_index
        """,
        (digest_id, topic_id),
    )

    sources = []
    for row in cur.fetchall():
        sources.append({
            "citation_id": row[0],
            "chunk_id": row[1],
            "document_id": row[2],
            "citation_type": row[3],
            "excerpt": row[4] or row[6][:500] if row[6] else None,  # Fallback to chunk_text
            "chunk_index": row[5],
            "document": {
                "title": row[7],
                "author": row[8],
                "url_original": row[9],
                "saved_at": row[10],
                "category": row[11],
            },
        })

    return {
        "topic_id": topic_row[0],
        "topic_index": topic_row[1],
        "topic_name": topic_row[2],
        "summary": topic_row[3],
        "chunk_count": topic_row[4],
        "key_points": json.loads(topic_row[5]) if topic_row[5] else [],
        "source_count": len(sources),
        "sources": sources,
    }
```

#### Change 4: Update get_generated_digest to use normalized tables

**Location:** `get_generated_digest()` method, around line 2906

**Modify to prefer normalized data:**

```python
def get_generated_digest(self, digest_id: int) -> dict[str, Any] | None:
    """Get a generated digest by ID (excludes soft-deleted).

    Prefers normalized tables (digest_topics) over JSON blob.
    Falls back to topics_json for backward compatibility with old digests.
    """
    cur = self.conn.execute(
        """
        SELECT id, name, title, time_range_days, date_from, date_to, strategy, model_id,
               summary_text, topics_json, highlights_json,
               docs_analyzed, chunks_analyzed, tokens_input, tokens_output, cost_usd,
               generated_at, is_favorite
        FROM generated_digests WHERE id = ? AND deleted_at IS NULL
        """,
        (digest_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    # Try to get topics from normalized table first
    topics = self.get_digest_topics(digest_id)
    if not topics:
        # Fall back to JSON blob for old digests
        topics = json.loads(row[9]) if row[9] else []
    else:
        # Enrich topics with citation counts
        for topic in topics:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM digest_citations WHERE topic_id = ?",
                (topic["id"],)
            )
            topic["source_count"] = cur.fetchone()[0]

    highlights = json.loads(row[10]) if row[10] else []

    return {
        "id": row[0],
        "name": row[1],
        "title": row[2],
        "time_range_days": row[3],
        "date_from": row[4],
        "date_to": row[5],
        "strategy": row[6],
        "model_id": row[7],
        "summary_text": row[8],
        "topics": topics,
        "highlights": highlights,
        "docs_analyzed": row[11],
        "chunks_analyzed": row[12],
        "tokens_input": row[13],
        "tokens_output": row[14],
        "cost_usd": row[15],
        "generated_at": row[16],
        "is_favorite": row[17],
    }
```

---

### 3.3 Phase A-3: Add Drill-Down API Endpoint

**File:** `app/main.py`

**Location:** After existing digest endpoints, around line 1830

**New endpoint:**

```python
@app.get("/api/digest/{digest_id}/topics/{topic_id}/sources")
async def api_digest_topic_sources(
    digest_id: int,
    topic_id: int,
    db: DB = Depends(get_db),
):
    """Get sources (citations with document context) for a digest topic.

    Returns the topic info plus list of source chunks with full document metadata.
    Used by frontend for "View Sources" drill-down.
    """
    result = db.get_topic_sources(digest_id, topic_id)
    if not result:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result
```

---

### 3.4 Phase A-4: Frontend Source Drill-Down UI

**File:** `app/templates/digest_home.html`

#### Change 1: Add source count badge to topic cards

**Location:** Topic card template, around line 203-216

**Current:**
```html
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
  <template x-for="topic in digest.topics" :key="topic.topic_index">
    <div class="card bg-base-200 p-4">
      <h4 class="font-semibold text-base-content" x-text="topic.topic_name"></h4>
      <p class="text-sm text-base-content/70 mt-1" x-text="topic.summary"></p>
      <div class="text-xs text-base-content/50 mt-2">
        <span x-text="topic.chunk_count"></span> Chunks
      </div>
    </div>
  </template>
</div>
```

**Target:**
```html
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
  <template x-for="topic in digest.topics" :key="topic.topic_index || topic.id">
    <div class="card bg-base-200 p-4">
      <div class="flex justify-between items-start">
        <h4 class="font-semibold text-base-content" x-text="topic.topic_name"></h4>
        <button
          class="btn btn-ghost btn-xs"
          @click="toggleSources(topic)"
          x-show="topic.source_count > 0"
        >
          <span class="badge badge-outline badge-sm" x-text="topic.source_count + ' sources'"></span>
        </button>
      </div>
      <p class="text-sm text-base-content/70 mt-1" x-text="topic.summary"></p>

      <!-- Key points (if available) -->
      <template x-if="topic.key_points && topic.key_points.length > 0">
        <ul class="mt-2 space-y-1">
          <template x-for="point in topic.key_points" :key="point">
            <li class="text-sm text-base-content/80 flex items-start gap-2">
              <span class="text-primary">-</span>
              <span x-text="point"></span>
            </li>
          </template>
        </ul>
      </template>

      <!-- Expandable sources panel -->
      <div
        x-show="topic.showSources"
        x-collapse
        class="mt-4 border-t border-base-300 pt-4"
      >
        <template x-if="topic.sourcesLoading">
          <div class="flex justify-center py-4">
            <span class="loading loading-spinner loading-sm"></span>
          </div>
        </template>
        <template x-if="!topic.sourcesLoading && topic.sources">
          <div class="space-y-3">
            <template x-for="source in topic.sources" :key="source.citation_id">
              <div class="card bg-base-100 p-3 text-sm">
                <div class="font-medium" x-text="source.document.title || 'Untitled'"></div>
                <div class="text-xs text-base-content/60 mt-1">
                  <span x-text="source.document.author || 'Unknown'"></span>
                  <span class="mx-1">|</span>
                  <span x-text="source.document.category"></span>
                </div>
                <p class="mt-2 text-base-content/80 italic" x-text="'\"' + (source.excerpt || '').substring(0, 200) + '...\"'"></p>

                <!-- Universal Content Actions -->
                <div class="flex gap-2 mt-2">
                  <button
                    class="btn btn-ghost btn-xs"
                    @click="showContext(source)"
                    title="View surrounding context"
                  >Context</button>
                  <a
                    :href="'/library/' + source.document_id"
                    class="btn btn-ghost btn-xs"
                    title="View full document"
                  >Full Text</a>
                  <a
                    x-show="source.document.url_original"
                    :href="source.document.url_original"
                    target="_blank"
                    class="btn btn-ghost btn-xs"
                    title="Open original source"
                  >Original <span class="text-xs">↗</span></a>
                </div>
              </div>
            </template>
          </div>
        </template>
      </div>

      <div class="text-xs text-base-content/50 mt-2">
        <span x-text="topic.chunk_count || topic.source_count"></span> Chunks
      </div>
    </div>
  </template>
</div>
```

#### Change 2: Add Alpine.js methods for source loading

**Location:** Alpine.js data section, around line 260

**Add to Alpine data:**
```javascript
// Source drill-down state
expandedTopicId: null,

// Methods
async toggleSources(topic) {
  if (topic.showSources) {
    topic.showSources = false;
    return;
  }

  // Load sources if not already loaded
  if (!topic.sources) {
    topic.sourcesLoading = true;
    topic.showSources = true;

    try {
      const response = await fetch(`/api/digest/${this.digest.id}/topics/${topic.id}/sources`);
      if (response.ok) {
        const data = await response.json();
        topic.sources = data.sources;
      }
    } catch (e) {
      console.error('Failed to load sources:', e);
    } finally {
      topic.sourcesLoading = false;
    }
  } else {
    topic.showSources = true;
  }
},

showContext(source) {
  // TODO Phase A-4b: Modal with surrounding chunk context
  alert('Context view coming soon. Chunk ' + source.chunk_index + ' of document.');
},
```

---

## 4. Database Migration

### 4.1 Schema Changes

| Table | Change | Migration |
|-------|--------|-----------|
| `digest_topics` | Add `key_points_json TEXT` | `ALTER TABLE ... ADD COLUMN` |
| `documents` | Add `reader_url TEXT` | `ALTER TABLE ... ADD COLUMN` (Phase A+) |

### 4.2 Backward Compatibility

1. **Old digests without citations:** Will fall back to `topics_json` blob
2. **New digests:** Will use normalized tables, `topics_json` kept for emergency fallback
3. **No data migration required:** Old data remains valid, new data uses new path

### 4.3 Deprecation Path

```
Phase A:  topics_json written (for compat) + normalized tables populated
Phase B+: topics_json still written but marked deprecated in schema comments
Phase C+: Consider removing topics_json writes (keep reads for old data)
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

| Test | File | Description |
|------|------|-------------|
| `test_compile_phase_creates_citations` | `tests/test_digest_pipeline.py` | Verify citations created for each chunk |
| `test_get_topic_sources_returns_documents` | `tests/test_storage.py` | Verify JOIN returns document metadata |
| `test_backward_compat_old_digest` | `tests/test_storage.py` | Verify old digests still readable |

### 5.2 Integration Tests

| Test | Description |
|------|-------------|
| Full pipeline run → verify citations in DB | End-to-end citation creation |
| API endpoint returns sources with documents | Drill-down API works |
| Frontend loads sources on click | UI integration |

### 5.3 Manual Verification Checklist

- [ ] Generate new digest → verify `digest_topics` has rows
- [ ] Generate new digest → verify `digest_citations` has rows for each chunk
- [ ] Load digest in UI → topics show source count badge
- [ ] Click source badge → sources expand with document titles
- [ ] Click "Original ↗" → opens external URL
- [ ] Load OLD digest (pre-Phase A) → still renders correctly

---

## 6. Rollback Plan

If issues discovered after deployment:

1. **Immediate:** Set feature flag to disable citation UI (show old view)
2. **Data safe:** Old `topics_json` still present, no data lost
3. **Code rollback:** Revert `_compile_phase` changes, citations stop being written
4. **Cleanup:** New citations can be deleted if needed (no dependencies yet)

---

## 7. Future Phase Hooks

### Prepared for Phase B (Interactive Curation)

```sql
-- Curation state will link to digest_topics.id
CREATE TABLE digest_curation (
  digest_id INTEGER,
  topic_id INTEGER REFERENCES digest_topics(id),  -- ← Phase A provides this
  included BOOLEAN,
  rating INTEGER,
  ...
);
```

### Prepared for Phase C (Draft Bridge)

```sql
-- Draft will link to curated citations
CREATE TABLE draft_sources (
  draft_id INTEGER,
  citation_id INTEGER REFERENCES digest_citations(id),  -- ← Phase A provides this
  ...
);
```

### Prepared for Phase E (Lens System)

```sql
-- Lens will be linked at digest creation
ALTER TABLE generated_digests ADD COLUMN lens_id INTEGER;  -- ← Schema ready
```

---

## 8. Acceptance Criteria

### Must Have (Phase A Complete)

- [ ] Every new digest has rows in `digest_topics` table
- [ ] Every chunk in every topic has a row in `digest_citations`
- [ ] API endpoint `/api/digest/{id}/topics/{topic_id}/sources` returns data
- [ ] Frontend shows source count badge on each topic
- [ ] Clicking badge expands to show source excerpts with document titles
- [ ] Old digests (pre-Phase A) still load and display correctly

### Nice to Have (Phase A Polish)

- [ ] Source excerpt highlights the relevant portion
- [ ] "Context" button shows surrounding chunks
- [ ] Loading states during source fetch
- [ ] Error handling if source fetch fails

---

## 9. Implementation Order

```
1. storage.py: Add key_points_json column migration
2. storage.py: Update save_digest_topic() signature
3. storage.py: Add get_topic_sources() method
4. storage.py: Update get_generated_digest() to prefer normalized
5. digest_pipeline.py: Pass chunk_metadata to _compile_phase
6. digest_pipeline.py: Update _compile_phase to save topics + citations
7. main.py: Add /api/digest/{id}/topics/{topic_id}/sources endpoint
8. digest_home.html: Add source badge and expandable panel
9. digest_home.html: Add Alpine.js methods for source loading
10. Test manually with new digest generation
11. Verify old digests still work
```

---

## 10. Open Questions

1. **Excerpt length:** 500 chars enough? Or configurable?
2. **Source ordering:** By document date (current) or by relevance score?
3. **Chunk context:** How many surrounding chunks to show in "Context" view?
4. **Performance:** Index on `digest_citations(topic_id)` sufficient for large digests?

---

**Document Status:** Ready for review
**Next Step:** Approve spec, then begin implementation at step 1
