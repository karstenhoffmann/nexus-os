nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Highlights werden in DB gespeichert und in Detailansicht angezeigt.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Job-Loeschfunktion in UI
2) Cancel-Button fuer laufende Jobs
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Job-Liste aktualisiert sich jetzt live waehrend Import (Alpine.js Polling alle 3s)
- Neuer Endpoint /readwise/import/jobs-partial (app/main.py:283-288)
- Partial Template app/templates/partials/job_list.html
- Polling startet bei status running/starting/resuming, stoppt automatisch
- preflight-fast gruen
