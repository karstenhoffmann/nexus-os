nexus-os Status

Stand (kurz)
- Repo + Guardrails stehen: preflight-fast/deep, editorconfig, redacted compose config, Claude Hooks.
- App startet via docker compose (FastAPI + HTMX UI Grundseiten).
- sqlite-vec ist aktiv (linux/amd64 gepinnt), Daten bleiben lokal in _local (ignored).

Aktuelles Ziel
- Machbarkeits-Slice: Readwise read-only Preview (Artikel + Highlights) in der UI anzeigen.

Naechste Schritte (Claude Code, max 3)
1) Readwise: API Machbarkeit klaeren (Endpoints), minimalen Article/Highlight DTO definieren (provider-agnostisch).
2) Readwise Preview implementieren: read-only fetch + Anzeige, noch kein Persistieren.
3) Optional: favicon.ico hinzufuegen (kosmetisch).

Offene Fragen (max 3)
- Welche Readwise Endpoints liefern Volltext-Artikel vs Highlights (Readwise API vs Reader API)?
- Welche Felder sind minimal fuer Article/Highlight inkl. Original-URL (nicht Reader URL)?

Handoff
- UI Smoke Test abgeschlossen: alle 5 Seiten laden (200 OK), keine JS-Fehler, nur favicon fehlt (kosmetisch).
