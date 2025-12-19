nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen, Dark Mode, Feather Icons
- Library-Seite mit Tabellenansicht, Filtern und Sortierung (FTS + Semantic)
- Unified Sync Pipeline: Import -> Chunk -> Embed -> Index in einem Flow
- Drafts-Seite mit Versionierung (LinkedIn, Article, Note)

Aktuelles Ziel
- LLM-Powered Default Digest implementieren

Naechste Schritte (Claude Code, max 3)
1) Digest Phase 1: LLM Provider + DB-Schema
2) Digest Phase 2: Pipeline (Fetch, Cluster, Summarize, Compile)
3) Digest Phase 3-4: API + UI

Geplant (Detail-Plan)
- /Users/karsten/.claude/plans/luminous-juggling-biscuit.md
- Multi-Modell: GPT-4.1 nano/mini, GPT-4o-mini, GPT-5.x
- Zwei Strategien: Hybrid (Embedding->LLM) und Pure LLM
- Cached + Refresh, Admin-Konfiguration, Usage-Stats
- ~10 Tage in 6 Phasen

Handoff
- Digest-Plan erstellt (2025-12-19):
  - Vision: Wochenübersicht mit LLM-Summaries, Themen-Cluster, Highlights
  - Route: /digest (eigene Seite, nicht Startseite)
  - Neue Dateien: llm_providers.py, digest_job.py, digest_pipeline.py, digest_clustering.py
  - Kosten pro Digest: ~$0.003 (nano) bis ~$0.10 (GPT-5.2)

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
