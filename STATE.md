nexus-os Status

Stand (kurz)
- Streaming Import mit SSE-UI, DB-Persistierung und Rate Limit Handling fertig.
- Dedupe bei Re-Import jetzt via provider_id (nicht mehr via URL).
- Cancel-Button fuer laufende Jobs implementiert.
- Progress-Anzeige zeigt jetzt "X von Y" mit Gesamtzahl aus Readwise API.

Aktuelles Ziel
- Full-Import robust und vollstaendig.

Naechste Schritte (Claude Code, max 3)
1) Fehlerbehandlung/Retry fuer einzelne fehlgeschlagene Dokumente
2) Import-Statistik nach Abschluss (importiert, uebersprungen, Fehler)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Neues Feld items_total in ImportJob (import_job.py:40)
- DB-Schema erweitert + Migration (storage.py:84, 121-127)
- readwise.py liest count aus API-Response (Zeile 532-537)
- Progress-Events enthalten jetzt items_total
- UI zeigt "X von Y" in job_list.html, job_detail.html, readwise_import.html
- Progress-Bar berechnet echten Prozentwert wenn items_total bekannt
- preflight-fast gruen
