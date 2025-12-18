nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen, Dark Mode, Feather Icons
- Library-Seite mit Tabellenansicht, Filtern und Sortierung (FTS + Semantic)

Aktuelles Ziel
- Drafts-Seite implementieren

Naechste Schritte (Claude Code, max 3)
1) Feature Development: Drafts-Seite
2) Optional: Digests-Feedback einarbeiten
3) Optional: Doppelte Embeddings pruefen (8 Stueck)

Handoff
- FTS-Index repariert (2025-12-18):
  - documents_fts war korrupt ("database disk image is malformed")
  - Geloest: DROP + CREATE + Repopulate (2638 Dokumente indexiert)
  - Keyword-Suche funktioniert jetzt wieder

- Library Tabellenansicht (Commit 3210fa1):
  - Neue Spalten: category, word_count (mit Backfill aus raw_json)
  - Filter-Pills: Volltext/Highlights, Kategorie-Filter mit Counts
  - Sortierbare Spalten: Titel, Autor, Typ, Datum, Woerter, Score
  - Chunk-Preview bei semantischer Suche
  - Kategorie-Badges farbcodiert

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0
