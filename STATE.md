nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient mit Reader API (v3) + Export API (v2) implementiert.
- Streaming Import Generator implementiert mit Pause/Resume Support.

Aktuelles Ziel
- Full-Import: Beide APIs (Reader + Export/Snipd) mit Streaming, Pause/Resume, Merge.

Naechste Schritte (Claude Code, max 3)
1) Import Routes (start/pause/resume/stream) in app/main.py
2) Import UI Template mit SSE (readwise_import.html)
3) Test E2E

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Phase 2 Schritt 5 erledigt: Streaming Import Generator (app/providers/readwise.py)
- ImportEvent Dataclass mit type + data + to_sse() Methode
- ImportEventType Enum: item, progress, paused, completed, error
- stream_import() Generator: Reader API zuerst, dann Export API
- URL-basiertes Merging: url_index Dict trackt normalisierte URLs
- Pause-Check bei jeder Iteration fuer sofortiges Anhalten
- Progress Events alle 10 Items
- Plan: /Users/karsten/.claude/plans/linked-swimming-dragon.md
- preflight-fast gruen
