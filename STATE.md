nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System mit CSS-Variablen, Dark Mode, Feather Icons
- Library-Seite mit Tabellenansicht, Filtern und Sortierung (FTS + Semantic)
- Unified Sync Pipeline: Import -> Chunk -> Embed -> Index in einem Flow
- Drafts-Seite mit Versionierung (LinkedIn, Article, Note)
- Admin Prompt-Management mit Registry-Pattern (getestet, funktioniert)

Aktuelles Ziel
- UI Design Review: Hardcoded Colors beheben

Naechste Schritte (Claude Code, max 3)
1) Hardcoded Colors ersetzen (~80 rgba/hex-Werte in Templates)
2) Fehlende Variablen in app.css ergaenzen (purple, linkedin, modal-overlay)
3) Icon-Size Utilities definieren

Geplant (Detail-Plan)
- /Users/karsten/.claude/plans/floating-strolling-biscuit.md
- Multi-Modell: GPT-4.1 nano/mini, GPT-4o-mini, GPT-5.x
- Zwei Strategien: Hybrid (Embedding->LLM) und Pure LLM
- Cached + Refresh, Admin-Konfiguration, Usage-Stats

Handoff
- UI Design Review IN PROGRESS (2025-12-19):
  - Review durchgefuehrt: Design-System Score 7.4/10
  - ERLEDIGT: Undefined CSS Variables (commit 4a151f1)
    - --border-color -> --border (19x)
    - --bg-primary -> --bg-card (3x)
    - --text-primary -> --text (5x)
    - --accent -> --primary (7x)
    - --bg-muted/--bg-code/--bg-tertiary -> --bg-secondary (8x)
  - OFFEN: ~80 hardcoded rgba/hex Colors in Templates
    - Hauptsaechlich in: admin_embeddings, admin_fetch, library_results, document_detail
    - Pattern: rgba(120,120,120,*) und #dc2626/#22c55e etc.
  - OFFEN: Fehlende Variablen in app.css (purple, linkedin, twitter, modal-overlay)
  - OFFEN: Icon-Size Utilities (.icon-xs bis .icon-xl)

- Admin Prompt-Management KOMPLETT (2025-12-19):
  - app/core/prompts.py: DEFAULT_PROMPTS Registry mit 3 Prompts
  - DB-Tabelle prompt_templates fuer Custom Overrides
  - Admin-UI /admin/prompts: Modal-Editor, Variablen-Referenz, Reset-to-Default
  - APIs: GET/PUT /api/admin/prompts/{key}, POST /reset
  - Playwright-Test erfolgreich: Edit, Save, Reset, Digest-Generierung
  - Neuer Digest mit Registry: "KI, Vorhersagbarkeit & Verantwortlichkeit", $0.0018

- Digest Feature KOMPLETT (2025-12-19):
  - /digest Seite mit Generierung, History, Favoriten, Soft-Delete
  - Pipeline: fetch -> cluster -> summarize -> compile mit SSE-Progress
  - Modelle: GPT-4.1 nano/mini, GPT-4o mini, GPT-4o
  - Strategien: Hybrid (Embeddings + LLM) und Pure LLM
  - Kosten: $0.002 (nano) bis $0.03 (GPT-4o) pro Digest

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
