nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Highlights werden in DB gespeichert und in Detailansicht angezeigt.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Live-Update der Job-Liste waehrend laufendem Import (HTMX polling oder SSE)
2) Job-Loeschfunktion in UI
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Job-Liste zeigt jetzt abgeschlossene Jobs aus DB (app/core/import_job.py:173-185, app/main.py:157)
- Neue Methode list_recent() holt letzte 10 Jobs aus DB inkl. completed
- preflight-fast gruen
