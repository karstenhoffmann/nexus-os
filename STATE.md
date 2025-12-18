nexus-os Status

Stand (kurz)
- Duale Speicherung: fulltext (sauber) + fulltext_html (Original mit Bildern)
- Migration abgeschlossen: 1686 Dokumente HTML bereinigt, Original gesichert
- 69.338 Chunks bereit fuer Embeddings
- 55 Tests bestanden

Aktuelles Ziel
- Embeddings fuer alle Chunks generieren (~69k)

Fertig (diese Session)
1) fulltext_html Spalte hinzugefuegt (Original-HTML mit Bildern)
2) extract_text_from_html() mit Fallback fuer HTML-Fragmente
3) save_article() aktualisiert fuer Dual-Speicherung
4) Migration-Endpoint aktualisiert (/api/admin/clean-html-fulltext)
5) 1686 Dokumente migriert (HTML -> fulltext_html, bereinigt -> fulltext)
6) 8 reine Bild-Dokumente behandelt (nur fulltext_html, kein Text)

Naechste Schritte (Claude Code, max 3)
1) Embeddings generieren: curl -X POST "http://localhost:8000/api/embeddings/generate-chunks?limit=500"
2) Semantische Suche testen nach Embedding-Generierung
3) Optional: Commit + Push der Aenderungen

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Architektur-Entscheidung: Duale Speicherung
  - fulltext: Sauberer Text fuer Suche, Chunks, Embeddings
  - fulltext_html: Original HTML mit Bildern fuer zukuenftige Anzeige

- Neue/geaenderte Dateien:
  - content_fetcher.py:350-412 - extract_text_from_html() mit Fallback
  - storage.py:560-584 - INSERT mit fulltext_html
  - storage.py:508-555 - UPDATE mit fulltext_html
  - main.py:1023-1037 - Import mit Dual-Speicherung
  - main.py:560-631 - Migration-Endpoint aktualisiert

- Status nach Migration:
  - Total Dokumente: 2638
  - Mit sauberem Fulltext: 2159
  - Mit HTML-Backup: 1686
  - Total Chunks: 69.338
  - Chunks ohne Embeddings: 69.338

- Tests: docker compose exec app python -m pytest tests/ -v (55/55)
- Preflight: ./scripts/preflight-fast.sh (gruen)
