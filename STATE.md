nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert mit Chunk-Zitaten und Kontext.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion: OpenAI + Ollama Support mit Health-Checks.
- ContentFetcher: trafilatura fuer Fulltext-Extraktion von URLs.
- FetchJobStore: Job-Management mit Pause/Resume/Cancel.
- Fetch API: Alle Endpoints + SSE Streaming implementiert.
- Admin Fetch UI: /admin/fetch mit Live-Fortschritt.

Aktuelles Ziel
- Fulltext-Fetching (Plan: glistening-seeking-snowglobe.md)

Fertig (diese Session)
1) Sprint F1: ContentFetcher mit trafilatura
2) Sprint F2: FetchJobStore + DomainRateLimiter + run_fetch_job()
3) Sprint F3: API Endpoints + SSE Streaming
4) Sprint F4: Admin Fetch UI mit Alpine.js
5) 55 Tests bestanden

Naechste Schritte (Claude Code, max 3)
1) Sprint F5: Integration + Polish
2) Fulltext-Fetching starten und testen
3) Nach Fetch: Chunking + Chunk-Embeddings

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Admin Fetch UI: /admin/fetch
  - Statistiken: Dokumente, mit URL, mit Fulltext, ausstehend, fehlgeschlagen
  - Controls: Start/Pause/Resume/Cancel Buttons
  - Live Log: SSE Event Streaming
  - Job-Liste: Vorherige Jobs mit Status

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

- Alle Tests: docker compose exec app python -m pytest tests/ -v (55/55)

Wichtig: Sprint F5 (Integration + Polish) als naechstes!
