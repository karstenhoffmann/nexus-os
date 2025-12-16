nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient mit Reader API (v3) + Export API (v2) implementiert.
- Readwise Preview Route funktioniert, Einzelartikel mit Highlights.

Aktuelles Ziel
- Full-Import: Beide APIs (Reader + Export/Snipd) mit Streaming, Pause/Resume, Merge.

Naechste Schritte (Claude Code, max 3)
1) ImportJob Modell + Store erstellen (app/core/import_job.py)
2) Streaming Import Generator implementieren
3) Import Routes (start/pause/resume/stream) + UI

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Phase 1 komplett: Export API (v2) implementiert + getestet
- Neue Methoden: fetch_export_books(), _parse_export_book(), _parse_export_highlight()
- ID-Prefix geaendert: reader: fuer Reader API, export: fuer Export API
- URL-Normalisierung fuer Merge-Matching hinzugefuegt
- Snipd-Podcasts werden korrekt gefetcht (category=podcasts, provider=snipd)
- highlight_sources Feld zu Article DTO hinzugefuegt
- Plan: /Users/karsten/.claude/plans/linked-swimming-dragon.md
- preflight-fast gruen
