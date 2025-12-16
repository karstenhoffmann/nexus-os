nexus-os Status

Stand (kurz)
- Repo + Guardrails + App lauffaehig (FastAPI + HTMX + sqlite-vec).
- ReadwiseClient mit Reader API (v3) + Export API (v2) implementiert.
- Streaming Import mit SSE-UI fertig und E2E getestet.

Aktuelles Ziel
- Full-Import: Persistierung in DB + Rate Limit Handling.

Naechste Schritte (Claude Code, max 3)
1) Rate Limit Handling (Retry mit Backoff bei 429)
2) Artikel in DB speichern (nicht nur streamen)
3) Resume nach Fehler (Cursor persistieren)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- Phase 2 Schritte 5-7 erledigt: Import Routes + UI + E2E Test
- Import Routes in app/main.py:141-237 (start, pause, resume, stream, status)
- Import UI in app/templates/readwise_import.html mit Alpine.js + SSE
- E2E Test erfolgreich: 1916 Items importiert, dann Rate Limit (429)
- SSE Streaming funktioniert, Live Log zeigt Artikel-Titel
- Navigation: "Import" Link in base.html hinzugefuegt
- preflight-fast gruen
