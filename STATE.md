nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert mit Chunk-Zitaten und Kontext.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion: OpenAI + Ollama Support mit Health-Checks.
- ContentFetcher: trafilatura fuer Fulltext-Extraktion von URLs.
- FetchJobStore: Job-Management mit Pause/Resume/Cancel.
- Fetch API: Alle Endpoints + SSE Streaming implementiert.

Aktuelles Ziel
- Fulltext-Fetching (Plan: glistening-seeking-snowglobe.md)

Fertig (diese Session)
1) Sprint F1: ContentFetcher mit trafilatura
2) Sprint F2: FetchJobStore + DomainRateLimiter + run_fetch_job()
3) Sprint F3: API Endpoints + SSE Streaming
4) 55 Tests bestanden

Naechste Schritte (Claude Code, max 3)
1) Sprint F4: Admin Fetch UI (/admin/fetch)
2) Sprint F5: Integration + Polish
3) Fulltext-Fetching starten und testen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Fetch API Endpoints:
  POST /api/fetch/start           - Job starten
  POST /api/fetch/{id}/pause      - Job pausieren
  POST /api/fetch/{id}/resume     - Job fortsetzen
  POST /api/fetch/{id}/cancel     - Job abbrechen
  GET  /api/fetch/{id}/status     - Job Status
  GET  /api/fetch/{id}/stream     - SSE Stream
  GET  /api/fetch/stats           - Statistiken
  GET  /api/fetch/failures        - Fehler-Liste
  POST /api/fetch/retry-failed    - Retryable Fehler loeschen
  GET  /api/fetch/jobs            - Job-Liste
  DELETE /api/fetch/{id}          - Job loeschen

- Admin Page: GET /admin/fetch (Template fehlt noch - Sprint F4)

- Test mit curl:
  curl -X POST http://localhost:8000/api/fetch/start
  curl http://localhost:8000/api/fetch/stats

- Alle Tests: docker compose exec app python -m pytest tests/ -v (55/55)

Wichtig: Sprint F4 (Admin UI) als naechstes!
