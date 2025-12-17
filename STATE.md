nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Cancel-Button fuer laufende Jobs implementiert.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) (offen)
2) (offen)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Cancel-Funktion fertig: POST /readwise/jobs/{job_id}/cancel (app/main.py:291-297)
- Neuer Status CANCELLED in ImportStatus (import_job.py:23)
- ImportJobStore.cancel() setzt Status und persistiert (import_job.py:211-222)
- readwise.py prueft jetzt auf PAUSED und CANCELLED in allen Stream-Schleifen
- Cancel-Button in job_list.html fuer running/pending Jobs (btn-warning)
- CSS: btn-warning (Bootstrap-Konvention) in app.css
- Loeschen jetzt auch fuer cancelled Jobs erlaubt
- preflight-fast gruen
