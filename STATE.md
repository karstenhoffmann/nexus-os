nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Highlights werden in DB gespeichert und in Detailansicht angezeigt.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Cancel-Button fuer laufende Jobs
2) (offen)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Job-Loeschfunktion fertig: DELETE /readwise/jobs/{job_id} (app/main.py:291-302)
- Loeschen nur fuer completed/failed Jobs, nicht fuer running/pending
- Button in job_list.html mit HTMX delete + confirm dialog
- CSS: btn-sm, btn-danger (Bootstrap-Konvention) in app.css
- import_job.py delete() loescht jetzt auch completed Jobs aus DB
- CLAUDE.md: Punkt 8 "Vor Erweiterungen: Bestand pruefen" hinzugefuegt
- preflight-fast gruen
