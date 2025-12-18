nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert mit Chunk-Zitaten und Kontext.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion: OpenAI + Ollama Support mit Health-Checks.
- Fulltext-Fetching: Komplett implementiert (F1-F5).
  - ContentFetcher mit trafilatura
  - FetchJobStore mit Pause/Resume/Cancel
  - API Endpoints + SSE Streaming
  - Admin UI mit Live-Fortschritt
  - Next Steps Card (Chunks + FTS Rebuild)

Aktuelles Ziel
- Fulltext-Fetching starten und testen

Fertig (diese Session)
1) Sprint F1-F4: Fulltext Fetching System
2) Sprint F5: Integration + Polish
   - Fetch Stats erweitert (without_chunks)
   - FTS Rebuild Endpoint
   - Next Steps Card in Admin Fetch UI
   - Memory Optimierung (trafilatura cache reset)
3) 55 Tests bestanden

Naechste Schritte (Claude Code, max 3)
1) Fulltext-Fetching starten (/admin/fetch)
2) Chunks + Embeddings generieren
3) Semantische Suche mit Zitaten testen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Admin Fetch UI: /admin/fetch
  - Statistiken: Dokumente, mit URL, mit Fulltext, ausstehend, fehlgeschlagen
  - Controls: Start/Pause/Resume/Cancel Buttons
  - Live Log: SSE Event Streaming
  - Next Steps: Chunks generieren + FTS Rebuild
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

- Neue Endpoints:
  POST /admin/fts/rebuild         - FTS Index neu aufbauen

- Alle Tests: docker compose exec app python -m pytest tests/ -v (55/55)

Bereit: Fulltext-Fetching kann gestartet werden!
