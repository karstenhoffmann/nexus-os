nexus-os Status

Stand (kurz)
- Readwise Import mit withHtmlContent aktiviert (fulltext direkt von Readwise)
- fulltext_source Tracking implementiert ('readwise', 'trafilatura', 'manual')
- trafilatura Fallback fuer Dokumente ohne Readwise-Fulltext
- Provider-Abstraktion: OpenAI + Ollama Support

Aktuelles Ziel
- Sauberer Neuimport von Readwise mit Fulltext

Fertig (diese Session)
1) withHtmlContent=true im Reader API Import
2) fulltext_source Tracking in save_article()
3) 55 Tests bestanden

Naechste Schritte (Claude Code, max 3)
1) Datenbank-Reset durchfuehren
2) Readwise neu importieren (mit Fulltext)
3) Chunking + Embeddings generieren

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Aenderungen:
  - readwise.py:519 - withHtmlContent=true aktiviert
  - storage.py:468 - fulltext_source Parameter hinzugefuegt
  - storage.py:503-544 - fulltext_source wird bei Update gesetzt
  - storage.py:547-579 - fulltext_source wird bei Insert gesetzt
  - main.py:825-834 - fulltext_source='readwise' beim Import

- Reset-Anleitung (manuell):
  1) Container stoppen: docker compose down
  2) DB loeschen: rm _local/data/app.db
  3) Container starten: docker compose up -d
  4) Readwise importieren: /readwise/import
  5) Nach Import: /admin/fetch fuer Luecken (optional)
  6) Chunks generieren: /admin/fetch -> Next Steps

- Alle Tests: docker compose exec app python -m pytest tests/ -v (55/55)
