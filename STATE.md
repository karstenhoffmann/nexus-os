nexus-os Status

Stand (kurz)
- Full-Import mit URL-Dedupe und Text-Hash-Dedupe fertig.
- 2637 Dokumente, 1457 Highlights in DB - keine Duplikate.
- UI-Labels fuer nicht-technische Nutzer optimiert.

Aktuelles Ziel
- Dedupe-Import robust und getestet. (FERTIG)

Naechste Schritte (Claude Code, max 3)
1) (offen - naechstes Feature waehlen)
2) (offen)
3) (offen)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- URL-Dedupe in storage.py:save_article() - sucht erst per URL, dann UPSERT
- Text-Hash-Dedupe in storage.py:save_highlight() - UNIQUE(document_id, text_hash)
- Hilfsfunktionen: normalize_url(), text_hash(), normalize_highlight_text()
- UI-Labels korrigiert:
  - readwise_import.html: "Gemerged:" -> "Bereits vorhanden:", Log-Meldungen angepasst
  - partials/job_list.html: "merged" -> "bereits vorhanden", "X von Y" nur wenn X <= Y
- preflight-fast ausfuehren vor Commit
