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
- Library-Ansicht komplett ueberarbeitet (2025-12-18):
  - Neue Spalte "Highlights" mit Anzahl pro Dokument (sortierbar)
  - Datum zeigt jetzt: saved_at ODER erstes Highlight-Datum als Fallback
  - highlight_count in search_library() und search_library_semantic()
  - 464 highlight-only Dokumente werden korrekt mit Datum angezeigt
  - word_count ist NULL fuer bestehende Docs (wird bei Re-Import gefuellt)

- Detail-Seite redesigned (2025-12-18):
  - Markdown-Rendering via markdown2
  - Copy-Buttons fuer Highlights und Fulltext
  - Metadata-Grid mit category, word_count, dates

- Import-Pipeline gefixt:
  - category/word_count/saved_at werden jetzt bei Import gespeichert
  - Backfill-Migration setzt category='article' fuer alle bestehenden Docs

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0
