nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Highlights werden in DB gespeichert und in Detailansicht angezeigt.
- Library-Titel sind jetzt klickbar und fuehren zur Detailansicht.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Status-Anzeige in Job-Tabelle klickbar machen
2) DB-Migration testen (neue provider_id Spalte)
3) Import-Fortschritt in Job-Liste anzeigen (items_imported)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Dokumenten-Detailansicht: app/main.py:51-59
- get_document Methode: app/core/storage.py:161-186
- Template: app/templates/document_detail.html
- Library-Verlinkung: app/templates/library.html:14
- preflight-fast gruen
