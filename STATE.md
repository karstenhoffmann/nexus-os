nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- Readwise Reader API analysiert: v3/list liefert Dokumente + Volltext (withHtmlContent=true).
- Provider-agnostisches DTO (Article, Highlight) und ReadwiseClient implementiert.

Aktuelles Ziel
- Machbarkeits-Slice: Readwise read-only Preview (Artikel + Highlights) in der UI anzeigen.

Naechste Schritte (Claude Code, max 3)
1) Readwise Preview Route + Template: /readwise/preview mit Token-Eingabe, Dokument-Liste anzeigen.
2) Einzelartikel-Ansicht mit Highlights.
3) Optional: favicon.ico hinzufuegen (kosmetisch).

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- ReadwiseClient + DTOs fertig: app/providers/readwise.py, app/providers/content_types.py
- Settings erweitert um readwise_api_token
- preflight-fast gruen
