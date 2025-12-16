nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Highlights werden in DB gespeichert und in Detailansicht angezeigt.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Import-Fortschritt in Job-Liste anzeigen (items_imported)
2) Job-Liste: abgeschlossene Jobs aus DB laden (nicht nur Memory)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- DB-Migration fuer provider_id getestet und funktioniert (app/core/storage.py:104-118)
- preflight-fast gruen
