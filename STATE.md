nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI/Design System komplett (CSS-Variablen, Dark Mode, Feather Icons, keine hardcoded Farben)
- Library-Seite mit Tabellenansicht, Filtern und Sortierung (FTS + Semantic)
- Unified Sync Pipeline: Import -> Chunk -> Embed -> Index in einem Flow
- Drafts-Seite mit Versionierung (LinkedIn, Article, Note)
- Admin Prompt-Management mit Registry-Pattern (getestet, funktioniert)

Aktuelles Ziel
- Multi-Modell Feature (Plan in floating-strolling-biscuit.md)

Naechste Schritte (Claude Code, max 3)
1) Multi-Modell Feature planen und starten
2) -
3) -

Geplant (Detail-Plan)
- /Users/karsten/.claude/plans/floating-strolling-biscuit.md
- Multi-Modell: GPT-4.1 nano/mini, GPT-4o-mini, GPT-5.x
- Zwei Strategien: Hybrid (Embedding->LLM) und Pure LLM
- Cached + Refresh, Admin-Konfiguration, Usage-Stats

Handoff
- UI Design Review KOMPLETT (2025-12-19):
  - Review durchgefuehrt: Design-System Score 7.4/10
  - ERLEDIGT: Undefined CSS Variables (commit 4a151f1)
    - --border-color -> --border (19x)
    - --bg-primary -> --bg-card (3x)
    - --text-primary -> --text (5x)
    - --accent -> --primary (7x)
    - --bg-muted/--bg-code/--bg-tertiary -> --bg-secondary (8x)
  - ERLEDIGT: Hardcoded Colors in Templates (~92x ersetzt)
    - ERLEDIGT: admin_embeddings.html (18x ersetzt)
      - rgba(120,120,120,*) -> var(--bg-secondary), var(--bg-hover), var(--border), var(--text-muted)
      - rgba(59,130,246,*) -> var(--info-bg), var(--primary)
      - rgba(34,197,94,*) -> var(--success)
    - ERLEDIGT: admin_fetch.html (15x ersetzt)
      - rgba(120,120,120,*) -> var(--bg-secondary), var(--bg-hover), var(--border)
      - rgba(59,130,246,*) -> var(--info-bg)
    - ERLEDIGT: partials/library_results.html (16x ersetzt)
      - Badge-Farben: pdf->error, podcast/highlight->warning, video->success
      - Neue Variablen: --purple, --pink, --twitter, --linkedin in app.css
    - ERLEDIGT: document_detail.html (20x ersetzt)
      - Badge-Farben wie library_results.html
      - .card-error -> var(--error-bg/error)
      - Fallback #22c55e -> var(--success) korrigiert
    - ERLEDIGT: admin_prompts.html (15x ersetzt)
      - Modal: rgba(0,0,0,0.8) -> var(--modal-overlay)
      - Alle #ffffff/#242424 Fallbacks entfernt
      - Dark-Mode @media queries entfernt (CSS-Variablen reichen)
    - ERLEDIGT: admin_compare.html (8x ersetzt)
      - Inline styles -> class="text-success/text-error"
      - rgba(120,120,120,...) -> var(--bg-hover/bg-secondary/border)
    - sync.html: var(--success, #22c55e) Fallbacks (ok, nur Fallbacks)
  - ERLEDIGT: Fehlende Variablen in app.css ergaenzt:
    - --purple, --purple-bg (fuer epub Badge)
    - --pink, --pink-bg (fuer note Badge)
    - --twitter, --twitter-bg (fuer tweet Badge)
    - --linkedin, --linkedin-bg (fuer linkedin Badge)
    - --modal-overlay (fuer Modal-Hintergrund)
  - ERLEDIGT: Icon-Size Utilities in app.css:
    - .icon-xs (0.75rem), .icon-sm (1rem), .icon-md (1.25rem), .icon-lg (1.5rem), .icon-xl (2rem)

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
