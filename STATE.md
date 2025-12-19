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
1) Manueller Test: Neuen Digest generieren, SSE-Progress beobachten
2) Saved Queries von /digests zu eigenem Admin-Bereich verschieben
3) Digest History-Seite mit allen generierten Digests

Geplant (Detail-Plan)
- /Users/karsten/.claude/plans/luminous-juggling-biscuit.md
- Multi-Modell: GPT-4.1 nano/mini, GPT-4o-mini, GPT-5.x
- Zwei Strategien: Hybrid (Embedding->LLM) und Pure LLM
- Cached + Refresh, Admin-Konfiguration, Usage-Stats

Handoff
- Digest Phase 6: SSE-Progress Fix (2025-12-19):
  - Problem: PHASE_START Events fehlten in digest_pipeline.py
  - Fix: Jede Phase sendet jetzt PHASE_START mit Aktivitaets-Nachricht
  - Frontend zeigt currentActivity aus message-Feld
  - Token/Cost-Updates in PHASE_COMPLETE Events
  - UI zeigt live: Phase-Label, Activity-Text, Tokens, Kosten
  - Log zeigt: Chunks gefunden, Themen erstellt, Highlights generiert
  - Naechster Schritt: Manueller Test im Browser

- Digest Phase 5: Test mit echten Daten erfolgreich (2025-12-19):
  - Bugfixes: Storage->DB import, json import, total_cost_usd field name
  - JSON-Parsing fuer Topics und Highlights im Backend (nicht Template)
  - Erster Digest generiert: 428 Chunks -> 7 Topics, $0.007 (GPT-4.1-mini)
  - Themen: Claude Code, KI-Vertrauen, Vorhersagbarkeit, Codewandel, Bias, Schreibmuster
  - UI zeigt Summary, Highlights (5), Topics mit Chunk-Counts
  - Bekanntes Problem: SSE-Progress wird im UI nicht live angezeigt (Phase 6)

- Digest Phase 3+4: API Routes + UI erstellt (2025-12-19):
  - GET /digest: Hauptseite mit latest digest, generation controls
  - GET /api/digest/estimate: Kosten-Schaetzung (days, model)
  - POST /api/digest/generate: Startet Job, returns job_id
  - GET /api/digest/{job_id}/stream: SSE fuer Progress
  - GET /api/digest/{job_id}/status: Job-Status abrufen
  - GET /api/digest/latest: Letzten Digest abrufen
  - GET /api/digest/{digest_id}: Digest by ID
  - GET /api/digest/history: Liste aller Digests
  - DELETE /api/digest/{digest_id}: Digest loeschen
  - digest_home.html: Komplettes UI mit Alpine.js
    - Zeigt letzten Digest (Summary, Highlights, Topics)
    - Generation Form (Days, Model, Strategy)
    - Live Cost Estimate
    - SSE Progress mit Phasen
  - Navigation: /digests -> /digest (LLM Digest statt Saved Queries)
  - Naechster Schritt: Mit echten Daten testen

- Digest Phase 2c: digest_pipeline.py erstellt (2025-12-19):
  - run_digest_pipeline(): Async Generator fuer SSE-Streaming
  - 4 Phasen: _fetch_phase, _cluster_phase, _summarize_phase, _compile_phase
  - FETCH: Holt Chunks mit Embeddings (hybrid) oder ohne (pure_llm)
  - CLUSTER: Ruft cluster_chunks() auf, trackt Tokens/Cost
  - SUMMARIZE: Generiert Overall Summary + Highlights per LLM
  - COMPILE: Speichert Digest in DB via save_generated_digest()
  - estimate_digest(): Kosten-Schaetzung ohne LLM-Call
  - Tests: tests/test_digest_pipeline.py mit Mocks
  - Naechster Schritt: API Routes (Phase 3)

- Digest Phase 2b: digest_clustering.py erstellt (2025-12-19):
  - TopicCluster Dataclass mit topic_name, summary, chunk_ids, key_points
  - ClusteringResult mit Token/Cost-Tracking
  - hybrid_cluster(): k-means auf Embeddings + LLM fuer Naming/Summary
  - pure_llm_cluster(): LLM macht Clustering + Naming in einem Call
  - Neue DB-Methode: get_chunk_embeddings_in_date_range()
  - Test: 30 Chunks -> 5 Cluster in 0.7ms, $0.0007 (gpt-4.1-nano)
  - Naechster Schritt: digest_pipeline.py

- Digest Phase 2a: digest_job.py erstellt (2025-12-19):
  - DigestPhase: IDLE, FETCH, CLUSTER, SUMMARIZE, COMPILE, DONE
  - DigestStatus: PENDING, RUNNING, COMPLETED, FAILED
  - DigestEvent mit SSE-Serialisierung
  - DigestJob mit Token/Cost-Tracking
  - DigestJobStore (thread-safe, in-memory)

- Digest Phase 1 implementiert (2025-12-19):
  - llm_providers.py: OpenAIChatProvider (GPT-4.1 nano/mini, GPT-4o-mini, GPT-4o)
  - DB-Schema: llm_configs, generated_digests, digest_topics, digest_citations
  - DB-Methoden: get/set_llm_config, save/get_generated_digest, get_chunks_in_date_range
  - Health Check funktioniert: GPT-4.1-mini verbunden (Latency ~1.7s)
  - Kosten-Schaetzung: estimate_digest_cost() fuer 2000 Chunks = ~$0.33
  - Test: 428 Chunks im 7-Tage-Zeitraum verfuegbar

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
