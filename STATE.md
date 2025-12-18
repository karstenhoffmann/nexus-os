nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen und Dark Mode
- Digests-Feature komplett (Saved Queries mit FTS + Semantic)

Aktuelles Ziel
- App nutzen und ggf. weitere Verbesserungen

Naechste Schritte (Claude Code, max 3)
1) Feature Development: Drafts-Seite
2) Weitere UX-Verbesserungen
3) Optional: Doppelte Embeddings pruefen (8 Stueck)

Handoff
- Digests-Feature (Commit 1139548):
  - storage.py: CRUD-Funktionen, get_recent_highlights(), execute_digest_query()
  - main.py: /api/digests/{id}/results, /api/digests/{id}/count (HTMX)
  - digests.html: Alpine.js + HTMX mit Lazy-Loading
  - "Neueste Highlights" Default-Sektion
  - Click-to-expand Pattern fuer Ergebnisse
  - Beide Modi: FTS (Keyword) und Semantic

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0
