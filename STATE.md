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
- Library & Detail-Seite Verbesserungen (2025-12-18):
  - Bug gefixt: category/word_count wurden bei Import nicht gespeichert
  - save_article() um category/word_count Parameter erweitert
  - Readwise Events um word_count/saved_at erweitert
  - Backfill-Migration: alle Docs ohne category auf 'article' gesetzt
  - Neue Dependency: markdown2 fuer Markdown-Rendering
  - Detail-Seite komplett redesigned:
    - Metadata-Grid mit category, word_count, saved_at, published_at
    - Highlights mit Copy-Buttons (roher Markdown in Zwischenablage)
    - Fulltext mit Markdown-Rendering und Copy-Button
    - CSS-Variablen fuer Dark Mode Kompatibilitaet
  - WICHTIG: Nach Container-Neustart werden alle categories automatisch auf 'article' gesetzt
  - Testen: docker compose up --build, dann /library und /documents/{id} pruefen

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0
