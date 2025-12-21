# Nexus OS - Architecture

## Frontend Stack

### Core: Server-Rendered + Progressive Enhancement
- **Jinja2 templates** (server-rendered HTML)
- **HTMX** (partial updates without full page reload)
- **Alpine.js** (light client-side reactivity for toggles, modals, form feedback)
- **Tailwind CSS + DaisyUI** (utility classes + semantic component library)

### Why This Stack?
- Minimal build step (one-time CSS generation, no watch/bundler required)
- Server-rendered = works offline with caching, simple mental model
- DaisyUI = consistent components without custom CSS, easy theming/dark mode
- 10-year durability: HTML never breaks, CSS rarely breaks
- HyperUI as reference for layout patterns (copy-paste when needed)

### CSS Build (Offline-First)
All CSS is served locally (no CDN dependencies):
- **DaisyUI:** `app/static/daisyui.css` + `daisyui-themes.css` (downloaded from CDN, committed)
- **Tailwind:** `app/static/tailwind.css` (generated from templates)

Rebuild Tailwind after adding new utility classes:
```bash
./scripts/build-css.sh
```
Uses Tailwind standalone CLI (no Node.js required, macOS arm64 binary).

### Component Examples
```html
<!-- DaisyUI semantic classes -->
<button class="btn btn-primary">Save</button>
<div class="card bg-base-100 shadow-xl">...</div>
<input type="text" class="input input-bordered w-full" />

<!-- Still use Tailwind utilities for custom tweaks -->
<div class="card bg-base-100 shadow-xl mt-4 p-6">...</div>
```

## Backend Stack

### Core
- **Python 3.14** + **FastAPI**
- **Jinja2** for HTML templating
- **Pydantic** for data validation

### Why FastAPI?
- Modern async support
- Automatic OpenAPI docs
- Type hints throughout
- Simple dependency injection

## Database & Search

### Storage
- **SQLite** as System of Record (single file)
- **SQLite FTS5** for fulltext search
- **sqlite-vec** as SQLite extension for semantic/vector search

### Why SQLite?
- Portable (single file)
- Trivial backups (copy file)
- No extra servers to maintain
- sqlite-vec delivers semantic search without external infrastructure

### Risk & Mitigation
- **Risk:** sqlite-vec is pre-v1 and may have breaking changes
- **Mitigation:** VectorStore abstraction enables future swap without system rebuild

## Node.js Guidance

### Default: Python-First for App Runtime
- Prefer Python solutions for app runtime code
- Keeps stack simpler, fewer moving parts, easier 10-year maintenance

### Node.js Allowed Without Question
- `tests/e2e/` (Playwright browser tests)
- Development tooling (linters, formatters, scripts)

### Node.js in App Runtime: Propose First
If a feature would genuinely benefit from Node.js in the app runtime:
1. Claude must PROPOSE the tradeoff explicitly
2. Explain WHY Node is better for this specific case
3. Compare to Python alternatives
4. Let user decide

### What to Avoid
- Silently adding Node dependencies when Python alternatives exist
- Introducing build steps (webpack, vite, etc.) without discussion
- CDN dependencies that break offline-first requirement

## Confirm by Default Requirement

**All expensive operations require manual confirmation:**
- LLM calls (digest generation, summarization, clustering)
- Embedding generation (large batches)
- Web checks (fact-checking, research)
- Apify enrichment (network data)
- Large imports (>500 items)

**Every LLM/Embedding job must log:**
- Provider name
- Model ID
- Central parameters
- Cost estimate (when calculable)

**Defaults are conservative.** More expensive modes only after explicit confirm.

## Provider Abstraction

### LLM Providers
```python
# app/core/llm_providers.py
get_chat_provider(provider_name, model) -> LLMProvider

# Implementations:
# - OpenAIChatProvider (default)
# - Future: Anthropic, Mistral, OpenRouter
```

### Embedding Providers
```python
# app/core/embedding_providers.py
get_provider(provider_name, model) -> EmbeddingProvider

# Implementations:
# - OpenAIProvider (default)
# - OllamaProvider (local, free)
```

### Configuration (.env)
```
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=...
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### Provider Guardrails
1. **Model pinning per job:** provider + model stored, no silent switches
2. **Fallback without data migration:** provider change = config change only
3. **Embeddings versioned:** provider-specific, old embeddings preserved when switching
4. **Deep research transparent:** claims, sources, uncertainty always visible (not black box)

## Operations

### Docker Compose (Mandatory)
- Local and VPS environments identical
- Data in host-mounted `./data`, NOT container write layer
- Controlled build of sqlite-vec extension in image

### Backup & Restore
- Persistent data in `./data` on host
- Backup = copy `./data` folder
- GitHub contains only code, no data
- Restore: clone repo → copy back `./data` → set `.env` → `docker compose up`
- **Target:** Back to working state in under 30 minutes

## Data Model (High-Level)

### Content
- `documents`: id, source, provider_id, url_original, url_canonical, title, author, published_at, saved_at, fulltext, summary, raw_json
- `documents_fts`: FTS5 virtual table for fulltext search
- `highlights`: id, document_id, kind, text, text_hash, location, raw_json

### Chunks & Embeddings
- `chunks`: id, document_id, chunk_index, content, token_count
- `vec_chunks`: sqlite-vec table for semantic search

### Drafts
- `drafts`: id, status, kind, title, folder_id, tags
- `draft_revisions`: id, draft_id, text, references, user_feedback

### Network (Future - Phase 3+)
- `person`: person_id, canonical_key, linkedin_url, email, current_snapshot_id
- `person_snapshot`: snapshot_id, person_id, captured_at, source, headline, about, location, experience_json
- `organization` + `organization_snapshot` (analogous)
- `relationship`: type (works_at, knows, project_role), evidence

### Jobs
- `jobs`: job_id, type, state, cost_estimate, requires_confirm, payload_json
- `job_runs`: logs, timestamps, outputs

## Design System Rules

### Offline-First
- All UI elements must load without internet
- CSS/JS served from local static files (no CDN dependencies)

### Evidence-First
- Every data view must show `source_url` (provenance)
- Clear fallback when source unavailable

### Component Standards
- **Buttons:** Must have disabled state during HTMX requests (use `htmx-request` class)
- **Lists:** Large lists need server-side paging (FastAPI SQL LIMIT/OFFSET)
- **Errors:** Every API call needs error state in UI
- **Search Results:** Grouped by document (no chunk duplicates), with preview

### Responsive
- Desktop-first design (works perfectly at 1200px+)
- Mobile-acceptable (375px viewport must be usable)

## Testing Strategy

Priority: Data integrity and recoverability.

| Type | Location | Purpose |
|------|----------|---------|
| **Unit** | `tests/backend/` | dedupe keys, URL normalization, snapshot change detection |
| **Integration** | `tests/backend/` | Readwise fixtures, CSV fixtures, Apify fixtures |
| **Smoke** | `tests/backend/` | start, import, search, digest, draft |
| **E2E** | `tests/e2e/` | Playwright browser audits (Node.js allowed here) |

### Pre-commit Checks
- `./scripts/preflight-fast.sh` before every commit
- `./scripts/preflight-deep.sh` when Docker/deps/sqlite-vec affected
