nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Highlights werden in DB gespeichert und in Detailansicht angezeigt.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) DB-Migration testen (neue provider_id Spalte)
2) Import-Fortschritt in Job-Liste anzeigen (items_imported)
3) Job-Liste: abgeschlossene Jobs aus DB laden (nicht nur Memory)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Job-Detailansicht: app/main.py:283-290
- Template: app/templates/job_detail.html
- Job-Tabelle klickbar: app/templates/readwise_import.html:113-114
- preflight-fast gruen
