nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient + DTOs implementiert.
- Readwise Preview Route (/readwise/preview) mit Token-Eingabe und Dokument-Liste fertig.

Aktuelles Ziel
- Machbarkeits-Slice: Readwise read-only Preview (Artikel + Highlights) in der UI anzeigen.

Naechste Schritte (Claude Code, max 3)
1) UI testen: App starten, /readwise/preview oeffnen, Artikel anklicken, Highlights pruefen.
2) Optional: favicon.ico hinzufuegen (kosmetisch).
3) Optional: Readwise Link von Admin-Seite aus zugaenglich machen.

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Einzelartikel-Route /readwise/article/{id} fertig (main.py:106-134)
- Template readwise_article.html zeigt Titel, Autor, Highlights, Summary, HTML-Inhalt
- Machbarkeits-Slice komplett: Preview Liste + Einzelartikel + Highlights
- preflight-fast gruen
