nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen, Dark Mode, Feather Icons
- Library-Seite mit Tabellenansicht, Filtern und Sortierung

Aktuelles Ziel
- Drafts-Seite implementieren

Naechste Schritte (Claude Code, max 3)
1) FTS-Index reparieren (Datenbank-Korruption beheben)
2) Feature Development: Drafts-Seite
3) Optional: Digests-Feedback einarbeiten

Handoff
- Library Tabellenansicht (Commit 3210fa1):
  - Neue Spalten: category, word_count (mit Backfill aus raw_json)
  - Filter-Pills: Volltext/Highlights, Kategorie-Filter mit Counts
  - Sortierbare Spalten: Titel, Autor, Typ, Datum, Woerter, Score
  - Chunk-Preview bei semantischer Suche
  - Kategorie-Badges farbcodiert
  - FTS deaktiviert wegen DB-Korruption (separates Issue)

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0
