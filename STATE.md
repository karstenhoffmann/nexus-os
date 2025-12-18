nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert! /library?mode=semantic durchsucht via Vektor-Aehnlichkeit.
- FTS5-Volltextsuche weiterhin unter /library?mode=fts (Standard).
- 2637 Dokumente, 1457 Highlights in DB - Embeddings werden generiert.
- API-Endpoint: GET /api/semantic-search?q=...&limit=10

Aktuelles Ziel
- Semantische Suche (Epic C) - FERTIG, Embeddings werden generiert

Naechste Schritte (Claude Code, max 3)
1) Embedding-Generierung abwarten (laeuft im Hintergrund)
2) Lokales Embedding-Modell als Fallback einbauen (sentence-transformers)
3) Admin-UI: Provider-Auswahl (OpenAI vs Lokal)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Semantische Suche: /library mit mode=semantic oder /api/semantic-search
- Embedding-Stats: GET /admin/embeddings/stats
- Batch-Generierung: ./scripts/generate-all-embeddings.sh
- Troubleshooting OpenAI 429: Siehe README.md Abschnitt 5
- Externe API Regeln: Siehe CLAUDE.md Abschnitt 10
