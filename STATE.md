nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert mit Chunk-Zitaten und Kontext.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion: OpenAI + Ollama Support mit Health-Checks.
- Modell-Vergleich: /admin/compare fuer Side-by-Side Tests.
- Chunking-System: 800 Zeichen, 20% Ueberlappung, Positionsdaten.

Aktuelles Ziel
- KI-Modell-Konfiguration und Hybrid-Chunking (Plan: glistening-seeking-snowglobe.md)

Fertig (diese Session)
1) Sprint 1: Provider-Abstraktion (embedding_providers.py)
2) Sprint 2: DB-Schema (Chunks, Embeddings, Usage)
3) Sprint 3: Chunking-System (chunking.py)
4) Sprint 4: Modell-Vergleichs-UI (/admin/compare)
5) Sprint 5: Zitierbarkeit und Kontext (library.html mit Chunk-Zitaten)

Naechste Schritte (Claude Code, max 3)
1) Sprint 6: Admin-UI mit Provider-Auswahl und Erklaerungen
2) Sprint 7: Usage-Tracking Dashboard
3) Sprint 8: Query-Caching

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Provider-Vergleich: /admin/compare
- Chunk-Suche: /library?mode=semantic (zeigt Zitate wenn Chunks existieren)
- API Compare: GET /api/compare/search?q=...&provider=openai|ollama
- Chunk-Kontext: db.get_chunk_context(chunk_id, context_chunks=2)
- Alle Provider-Endpoints: /api/providers/*, /api/embeddings/*

Wichtig: Chunks muessen erst generiert werden!
  POST /api/embeddings/generate-chunks?limit=300

Danach funktioniert die Chunk-basierte Suche mit Zitaten.
