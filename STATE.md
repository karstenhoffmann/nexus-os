nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Import-Jobs werden in DB persistiert (Tabelle import_jobs).
- Resume nach Fehler/Neustart funktioniert: UI zeigt jetzt Resume-Banner.
- Highlights werden jetzt in DB gespeichert (Tabelle highlights).

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Dedupe bei Re-Import verbessern
2) Status-Anzeige in Job-Tabelle klickbar machen
3) Highlights in Artikel-Detailansicht anzeigen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- highlights Tabelle: app/core/storage.py:87-99 (Schema)
- save_highlight Methode: app/core/storage.py:255-288
- get_highlights_for_document: app/core/storage.py:290-310
- Highlights im SSE-Event: app/providers/readwise.py:649-659
- Highlights speichern im Import: app/main.py:232-243
- preflight-fast gruen
