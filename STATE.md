nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient + DTOs implementiert.
- Readwise Preview Route (/readwise/preview) mit Token-Eingabe und Dokument-Liste fertig.

Aktuelles Ziel
- Machbarkeits-Slice: Readwise read-only Preview (Artikel + Highlights) in der UI anzeigen.

Naechste Schritte (Claude Code, max 3)
1) Einzelartikel-Ansicht mit Highlights: /readwise/article/{id} Template + Route.
2) Optional: favicon.ico hinzufuegen (kosmetisch).
3) Optional: Readwise Link von Admin-Seite aus zugaenglich machen.

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- /readwise/preview Route fertig: Token-Eingabe oder aus .env, zeigt 20 Artikel
- Link in Navigation eingefuegt
- Naechster Schritt: Einzelartikel-Ansicht mit Highlights
- preflight-fast gruen
