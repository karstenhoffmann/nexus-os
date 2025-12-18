nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert! /library?mode=semantic durchsucht via Vektor-Aehnlichkeit.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion fertig: OpenAI + Ollama Support.
- Chunking-System fertig: 800 Zeichen Chunks mit 20% Ueberlappung.
- Neue DB-Tabellen: document_chunks, embeddings (mit Provider-Info), api_usage.

Aktuelles Ziel
- KI-Modell-Konfiguration und Hybrid-Chunking (Plan: glistening-seeking-snowglobe.md)

Fertig (diese Session)
1) Sprint 1: Provider-Abstraktion (app/core/embedding_providers.py)
2) Sprint 2: DB-Schema erweitern (Chunks, Embeddings, Usage-Tracking)
3) Sprint 3: Chunking-System (app/core/chunking.py)

Naechste Schritte (Claude Code, max 3)
1) Sprint 4: Modell-Vergleichs-UI (/admin/compare)
2) Sprint 5: Zitierbarkeit und Kontext in Such-Ergebnissen
3) Sprint 6: Admin-UI mit Provider-Auswahl und Erklaerungen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Provider-Abstraktion: app/core/embedding_providers.py
  - get_provider('openai'|'ollama', model) → EmbeddingProvider
  - OpenAIProvider, OllamaProvider mit health_check()
  - Modell-Info: OPENAI_MODELS, OLLAMA_MODELS

- Neue API-Endpoints:
  - GET /api/providers/health → Alle Provider pruefen
  - GET /api/providers/models → Verfuegbare Modelle
  - GET /api/providers/{provider}/health → Einzelner Provider
  - POST /api/embeddings/generate?provider=&model=&include_chunks=
  - POST /api/embeddings/generate-chunks
  - GET /api/embeddings/stats → Detaillierte Stats pro Provider
  - GET /api/chunking/info → Chunking-Parameter
  - GET /api/usage/stats?period=today|week|month|all

- Chunking: app/core/chunking.py
  - chunk_document(fulltext, title) → List[Chunk]
  - CHUNK_SIZE=800, CHUNK_OVERLAP=160

- Settings erweitert: EMBEDDING_PROVIDER, EMBEDDING_MODEL, OLLAMA_BASE_URL

- Troubleshooting OpenAI 429: Siehe README.md Abschnitt 5
- Plan-Datei: ~/.claude/plans/glistening-seeking-snowglobe.md
