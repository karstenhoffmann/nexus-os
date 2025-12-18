nexus-os Status

Stand (kurz)
- FTS5-Volltextsuche funktioniert. /library?q=suchbegriff durchsucht Titel, Autor, Volltext, Summary.
- 2637 Dokumente, 1457 Highlights in DB - keine Duplikate.
- sqlite-vec funktioniert - Tests bestaetigen Insert/Query mit 1536 Dimensionen.
- Admin-Endpoint fuer Embedding-Generierung fertig: POST /admin/embeddings/generate

Aktuelles Ziel
- Semantische Suche (Epic C) - in Arbeit

Naechste Schritte (Claude Code, max 3)
1) Embeddings generieren: Im Browser /admin oeffnen, Button klicken (100 pro Klick, kostet ca. $0.03 pro 100)
2) Aehnlichkeitssuche implementieren (semantic_search in storage.py)
3) Semantische Suche in UI einbauen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- POST /admin/embeddings/generate?limit=100 - generiert Embeddings fuer bis zu 100 Dokumente
- GET /admin/embeddings/stats - zeigt Statistik (total, embedded, pending)
- /admin UI zeigt Embedding-Statistik und Button zum Generieren
- Bei 2637 Dokumenten: ~27 Klicks oder curl-Schleife noetig
