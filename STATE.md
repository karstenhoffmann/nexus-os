nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Import-Jobs werden in DB persistiert (Tabelle import_jobs).
- Resume nach Fehler/Neustart funktioniert: UI zeigt jetzt Resume-Banner.
- Highlights werden jetzt in DB gespeichert (Tabelle highlights).
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Status-Anzeige in Job-Tabelle klickbar machen
2) Highlights in Artikel-Detailansicht anzeigen
3) DB-Migration testen (neue provider_id Spalte)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- documents Schema mit provider_id: app/core/storage.py:16-32
- save_article mit UPSERT: app/core/storage.py:173-217
- UNIQUE constraint auf (source, provider_id) fuer zuverlaessiges Dedupe
- preflight-fast gruen
