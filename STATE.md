nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Import-Jobs werden in DB persistiert (Tabelle import_jobs).
- Resume nach Fehler/Neustart funktioniert: UI zeigt jetzt Resume-Banner.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Highlights in DB speichern
2) Dedupe bei Re-Import verbessern
3) Status-Anzeige in Job-Tabelle klickbar machen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Resume-Banner: app/templates/readwise_import.html:8-27 (UI)
- resumable_job wird an Template uebergeben: app/main.py:147
- resumePreviousJob() JS-Funktion: app/templates/readwise_import.html:337-362
- get_resumable() Methode: app/core/import_job.py:173-183
- preflight-fast gruen
