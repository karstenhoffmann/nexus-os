nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert mit Chunk-Zitaten und Kontext.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion: OpenAI + Ollama Support mit Health-Checks.
- ContentFetcher: trafilatura fuer Fulltext-Extraktion von URLs.
- FetchJobStore: Job-Management mit Pause/Resume/Cancel.
- DomainRateLimiter: Adaptives Rate-Limiting pro Domain.

Aktuelles Ziel
- Fulltext-Fetching (Plan: glistening-seeking-snowglobe.md)

Fertig (diese Session)
1) Sprint F1: ContentFetcher mit trafilatura
2) Sprint F2: FetchJobStore + DomainRateLimiter + run_fetch_job()
3) 55 Tests bestanden

Naechste Schritte (Claude Code, max 3)
1) Sprint F3: API Endpoints + SSE Streaming (/api/fetch/*)
2) Sprint F4: Admin Fetch UI (/admin/fetch)
3) Sprint F5: Integration + Polish

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- FetchJobStore: from app.core.fetch_job import get_fetch_store
  - store.create(items_total=100) - Job erstellen
  - store.get(job_id) - Job abrufen
  - store.pause(job_id) - Job pausieren
  - store.cancel(job_id) - Job abbrechen
  - store.get_running() - Laufenden Job holen
  - store.get_resumable() - Pausierte/Failed Jobs

- DomainRateLimiter: Adaptives Rate-Limiting
  - MIN_DELAY=2s, MAX_DELAY=10s
  - Erhoeht Delay bei Fehlern, reset bei Erfolg

- run_fetch_job(): Async Generator fuer SSE
  - Yieldet FetchEvent (STARTED, PROGRESS, ITEM_SUCCESS, etc.)
  - event.to_sse() fuer Server-Sent Events Format

- Alle Tests: docker compose exec app python -m pytest tests/ -v (55/55)

Wichtig: Sprint F3 (API Endpoints) als naechstes!
