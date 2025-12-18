nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert (sqlite-vec KNN + Chunk-Metadaten)
- UI-Verbesserungen: Tabellen, Dark Mode Toggle, Nav Active State
- Orphan-Embeddings bereinigt (1.950 geloescht)

Aktuelles Ziel
- App nutzen und ggf. weitere Verbesserungen

Naechste Schritte (Claude Code, max 3)
1) Feature Development (Digests, Drafts)
2) Weitere UX-Verbesserungen
3) Optional: Doppelte Embeddings pruefen (8 Stueck)

Handoff
- Orphan-Cleanup:
  - cleanup_orphan_embeddings() in storage.py:1263-1317
  - POST /admin/embeddings/cleanup-orphans Endpoint in main.py:270-288
  - 1.950 verwaiste Embeddings geloescht
  - Admin zeigt jetzt 100% statt 103%
- Commit empfohlen

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: 0

