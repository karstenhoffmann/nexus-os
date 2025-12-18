nexus-os Status

Stand (kurz)
- FTS5-Volltextsuche funktioniert. /library?q=suchbegriff durchsucht Titel, Autor, Volltext, Summary.
- 2637 Dokumente, 1457 Highlights in DB - keine Duplikate.
- sqlite-vec funktioniert - Tests bestaetigen Insert/Query mit 1536 Dimensionen.
- Embedding-Generierung implementiert und getestet.

Aktuelles Ziel
- Semantische Suche (Epic C) - in Arbeit

Naechste Schritte (Claude Code, max 3)
1) Embeddings fuer bestehende Dokumente generieren (API-Aufruf)
2) Aehnlichkeitssuche implementieren (semantic_search in storage.py)
3) Semantische Suche in UI einbauen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- app/core/embed_job.py: generate_embeddings_batch() und generate_all_embeddings()
- storage.py: get_documents_without_embedding(), save_embedding(), get_embedding_stats()
- tests/test_embed_job.py: 7 Tests bestanden
- Embedding-Workflow: Dokumente ohne Embedding holen -> Batch-API -> serialize_f32 -> save_embedding
- Naechster Schritt: Admin-Endpoint oder CLI zum Starten der Embedding-Generierung
