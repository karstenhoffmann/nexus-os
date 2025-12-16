nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Import-Jobs werden jetzt in DB persistiert (Tabelle import_jobs).
- Resume nach Fehler/Neustart funktioniert: Cursor + Status bleiben erhalten.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) UI: Resume-Button fuer fehlgeschlagene/pausierte Jobs anzeigen
2) Highlights in DB speichern
3) Dedupe bei Re-Import verbessern

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- import_jobs Tabelle: app/core/storage.py:73-85 (Schema)
- ImportJobStore mit DB-Persistierung: app/core/import_job.py:81-193
- Automatische Initialisierung: app/core/storage.py:247 (init_import_store)
- Jobs werden bei jedem Event gespeichert: app/main.py:213 (store.update)
- get_resumable() Methode: gibt letzten failed/paused Job zurueck
- preflight-fast gruen
