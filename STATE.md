nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient mit Reader API (v3) + Export API (v2) implementiert.
- Streaming Import mit SSE-UI und DB-Persistierung fertig.
- Rate Limit Handling implementiert (Exponential Backoff bei 429).

Aktuelles Ziel
- Full-Import: Persistierung in DB.

Naechste Schritte (Claude Code, max 3)
1) Resume nach Fehler (Cursor persistieren)
2) Highlights in DB speichern
3) Dedupe bei Re-Import (bereits teilweise via URL-Match)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Artikel-Persistierung erledigt: save_article() in app/core/storage.py:141-211
- UPSERT-Logik: Wenn URL+source existiert -> Update, sonst Insert
- FTS-Index wird automatisch aktualisiert (_update_fts())
- Event-Daten erweitert: provider_id, author, summary, html_content, published_date
- Speicherung im SSE-Stream: app/main.py:215-228 (bei ITEM events)
- preflight-fast gruen
