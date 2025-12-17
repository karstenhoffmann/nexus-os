nexus-os Status

Stand (kurz)
- FTS5-Volltextsuche funktioniert. /library?q=suchbegriff durchsucht Titel, Autor, Volltext, Summary.
- 2637 Dokumente, 1457 Highlights in DB - keine Duplikate.
- Migration erstellt FTS-Tabelle automatisch fuer bestehende DBs.

Aktuelles Ziel
- FTS5-Suche eingebaut und getestet. (FERTIG)

Naechste Schritte (Claude Code, max 3)
1) (offen - naechstes Feature waehlen: semantische Suche, Digests, oder Drafts)
2) (offen)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- FTS5-Migration in storage.py:_run_migrations() - erstellt documents_fts und befuellt Index
- Suche ueber /library mit Parameter q
- search_documents() in storage.py:248 - FTS5 MATCH Query mit Relevanz-Ranking
- rebuild_fts() in storage.py:408 - wird nach Import automatisch aufgerufen
