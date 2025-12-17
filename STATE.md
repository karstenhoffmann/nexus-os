nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Cancel-Button fuer laufende Jobs implementiert.
- Progress-Anzeige zeigt jetzt "X von Y" mit Gesamtzahl aus Readwise API.
- Fehlerbehandlung fuer einzelne Dokumente: Import laeuft weiter bei Einzelfehlern.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Import-Statistik nach Abschluss (importiert, uebersprungen, Fehler) - UI verbessern
2) (offen)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Neues Feld items_failed in ImportJob (import_job.py:40)
- DB-Schema erweitert + Migration (storage.py:84, 130-132)
- readwise.py: try/except um einzelne Dokumente in _stream_reader_api (Zeile 549-596) und _stream_export_api (Zeile 648-717)
- Neuer Event-Typ ITEM_ERROR fuer Einzelfehler (readwise.py:26)
- UI zeigt items_failed in job_list.html, job_detail.html, readwise_import.html
- JavaScript handler fuer item_error Event in readwise_import.html
- preflight-fast gruen
