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
1) Digest Phase 3: API Routes (/digest, /api/digest/*)
2) Digest Phase 4: UI (digest_home.html)
3) Digest Phase 5: Test mit echten Daten

Geplant (Detail-Plan)
- /Users/karsten/.claude/plans/luminous-juggling-biscuit.md
- Multi-Modell: GPT-4.1 nano/mini, GPT-4o-mini, GPT-5.x
- Zwei Strategien: Hybrid (Embedding->LLM) und Pure LLM
- Cached + Refresh, Admin-Konfiguration, Usage-Stats
- ~10 Tage in 6 Phasen

Handoff
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
