nexus-os Status

Stand (kurz)
- FTS5-Volltextsuche funktioniert. /library?q=suchbegriff durchsucht Titel, Autor, Volltext, Summary.
- 2637 Dokumente, 1457 Highlights in DB - keine Duplikate.
- sqlite-vec funktioniert - Tests bestaetigen Insert/Query mit 1536 Dimensionen.

Aktuelles Ziel
- Semantische Suche (Epic C) - in Arbeit

Naechste Schritte (Claude Code, max 3)
1) Embedding-Funktion mit OpenAI API schreiben
2) Embeddings fuer bestehende Dokumente generieren
3) Aehnlichkeitssuche implementieren und in UI einbauen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Embedding-Modul app/core/embeddings.py fertig mit get_embedding() und get_embeddings_batch()
- Tests in tests/test_embeddings.py - 6 Tests bestanden
- serialize_f32() Funktion in embeddings.py serialisiert Vektoren fuer sqlite-vec
- doc_embeddings Tabelle existiert bereits (storage.py:232) mit float[1536]
- pytest-asyncio konfiguriert in pytest.ini
