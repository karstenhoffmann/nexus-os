nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen, Dark Mode, Feather Icons
- Digests-Feature komplett (Saved Queries mit FTS + Semantic)

Aktuelles Ziel
- Digests-Seite Feedback einarbeiten, dann Drafts

Naechste Schritte (Claude Code, max 3)
1) Digests-Feedback vom User einarbeiten
2) Feature Development: Drafts-Seite
3) Optional: Doppelte Embeddings pruefen (8 Stueck)

Handoff
- Feather Icons Integration (Commit b3be8f2):
  - base.html: CDN, Nav-Icons, Theme-Toggle (moon/sun)
  - app.css: Icon-Utilities (.icon-spin, .btn-icon, Status-Farben)
  - Alle Templates: Konsistente Icons fuer Aktionen, Status, Navigation
  - Chevrons fuer Expand/Collapse, Edit/Delete Icons, Job-Controls

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0
