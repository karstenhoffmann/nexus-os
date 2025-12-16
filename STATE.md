nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient mit Reader API (v3) + Export API (v2) implementiert.
- Readwise Preview Route funktioniert, Einzelartikel mit Highlights.

Aktuelles Ziel
- Full-Import: Beide APIs (Reader + Export/Snipd) mit Streaming, Pause/Resume, Merge.

Naechste Schritte (Claude Code, max 3)
1) Streaming Import Generator implementieren
2) Import Routes (start/pause/resume/stream) + UI
3) Import UI Template mit SSE

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Phase 2 Schritt 4 erledigt: ImportJob Modell + Store (app/core/import_job.py)
- ImportJob Dataclass mit Status, Cursors, Counters
- ImportJobStore: thread-safe In-Memory Store mit CRUD
- ImportStatus Enum: pending, running, paused, completed, failed
- Plan: /Users/karsten/.claude/plans/linked-swimming-dragon.md
- preflight-fast gruen
