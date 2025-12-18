nexus-os Status

Stand (kurz)
- Readwise Import ERFOLGREICH: 2167 Dokumente mit Fulltext (82%)
- 92.175 Chunks erstellt, Embeddings laufen (~1850 fertig)
- SQLite Concurrency Bug gefixt (log_api_usage)
- Provider-Abstraktion: OpenAI + Ollama Support

Aktuelles Ziel
- Embeddings fuer alle Chunks generieren (~92k)

Fertig (diese Session)
1) withHtmlContent=true im Reader API Import
2) fulltext_source Tracking
3) DB-Reset + sauberer Neuimport (2167 mit Fulltext)
4) 92.175 Chunks erstellt
5) SQLite Concurrency Bug gefixt
6) Embedding-Generierung funktioniert

Naechste Schritte (Claude Code, max 3)
1) Weitere Embeddings generieren (via /api/embeddings/generate-chunks)
2) Semantische Suche testen
3) Optional: trafilatura fuer 439 Dokumente ohne Fulltext

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Fixes in dieser Session:
  - storage.py:1217 - log_api_usage: lastrowid statt RETURNING
  - storage.py:946-1002 - save_embeddings_batch Methode
  - embed_job.py - Batch-Saving fuer Embeddings
  - main.py:429-481 - /api/chunks/generate Endpoint
  - main.py:490-513 - /api/chunking/unchunked Diagnose-Endpoint

- Root Cause des SQLite Bugs:
  - Symptom: "cannot commit transaction - SQL statements in progress"
  - Ursache: log_api_usage rief commit() VOR fetchone() auf
  - Loesung: Alle RETURNING-Klauseln durch lastrowid ersetzt

- Embedding-Statistik:
  - Total Chunks: 92.175
  - Mit Embeddings: ~1850 (2%)
  - Kosten bisher: ~$0.008
  - Geschaetzte Gesamtkosten: ~$0.37

- Embedding-Generierung fortsetzen:
  curl -X POST "http://localhost:8000/api/embeddings/generate-chunks?limit=500"

- Alle Tests: docker compose exec app python -m pytest tests/ -v (55/55)
