nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen, Dark Mode, Feather Icons
- Library-Seite mit Tabellenansicht, Filtern und Sortierung (FTS + Semantic)
- Unified Sync Pipeline: Import -> Chunk -> Embed -> Index in einem Flow
- Drafts-Seite mit Versionierung (LinkedIn, Article, Note)

Aktuelles Ziel
- Drafts weiter ausbauen (optional: LLM-Unterstuetzung)

Naechste Schritte (Claude Code, max 3)
1) Optional: Digests-Feedback einarbeiten
2) Optional: 11 Docs ohne Chunks pruefen
3) Optional: Drafts mit LLM-Vorschlaegen erweitern

Handoff
- Drafts-Seite implementiert (2025-12-19):
  - Listenansicht mit Status- und Typ-Filtern
  - Neuer Draft erstellen (linkedin, article, note)
  - Draft-Detail mit Titel-Edit, Status-Wechsel
  - Versionierung: neue Versionen mit Notizen speichern
  - Versionshistorie mit Expand/Collapse und Copy
  - Zeichenzaehler fuer LinkedIn (3000 Zeichen Limit)
  - Routes: /drafts, /drafts/new, /drafts/{id}
  - DB-Methoden: create_draft, get_draft, add_draft_version, update_draft_status/title

- Unified Sync Pipeline implementiert (2025-12-19):
  - Neue Seite /sync ersetzt /readwise/import
  - 4-Phasen Stepper: Import -> Chunk -> Embed -> Index
  - pipeline_job.py orchestriert bestehende Jobs (ImportJob, EmbedJob)
  - SSE Streaming fuer Live-Progress aller Phasen
  - Kosten-Schaetzung vor Embedding-Phase
  - Navigation aktualisiert: "Import" -> "Sync"
  - Alte Import-Seite bleibt erreichbar unter /readwise/import

- Kategorie-Normalisierung implementiert (2025-12-18):
  - normalize_category() in app/core/categories.py
  - Re-Sync durchgefuehrt: 2639 Docs mit echten Kategorien
  - LinkedIn (221), Podcast (428), PDF (96), Tweet (63), RSS (204), Book (32)

- Library komplett (2025-12-18):
  - Filter (Volltext/Highlights), Sortierung, Highlights-Spalte
  - Detail-Seite mit Markdown, Copy-Buttons

Status
- Total Docs: 2.639
- Mit Fulltext: 2.160
- Ohne Chunks: 11
- Total Chunks: 69.338
- Mit Embeddings: 69.338 (100%)
