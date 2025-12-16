nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient mit Reader API (v3) + Export API (v2) implementiert.
- Streaming Import mit SSE-UI fertig und E2E getestet.
- Rate Limit Handling implementiert (Exponential Backoff bei 429).

Aktuelles Ziel
- Full-Import: Persistierung in DB.

Naechste Schritte (Claude Code, max 3)
1) Artikel in DB speichern (nicht nur streamen)
2) Resume nach Fehler (Cursor persistieren)
3) Highlights in DB speichern

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Rate Limit Handling erledigt: _request_with_retry() in app/providers/readwise.py:110-175
- Exponential Backoff: 1s -> 2s -> 4s -> 8s (max 60s), max 5 Retries
- Retry-After Header wird beachtet
- Neue Exception: ReadwiseRateLimitError
- Alle API-Calls nutzen jetzt _request_with_retry()
- preflight-fast gruen
