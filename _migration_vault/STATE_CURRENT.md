# Projekt-Status (Nexus OS)

## Aktueller Fokus

- Design System Finalisierung & UX-Hardening.

## Nächste Schritte (Prio)

1. [ ] **Mobile Audit**: Navigation + kritische Seiten (375px Viewport)
2. [ ] **Draft System MVP**: Revisionen, Parken/Finalisieren (Phase 1)

## Erledigt

- Bugfix: SSE-Streaming - Pipeline lief in async Generator mit blockierendem Code, Events wurden nicht gesendet. Thread-basierter Wrapper implementiert (Dec 2025).
- Bugfix: SQLite-Version-Mismatch - FTS-Tabellen von Host (3.51.1) waren inkompatibel mit Container (3.46.1). Rebuild muss aus Container erfolgen (Dec 2025).
- UX: Import-Progress zeigt jetzt "X / Y Dokumente" statt "Verbinde mit Readwise API...", Prozent auf max 100% begrenzt (Dec 2025).
- Bugfix: FTS-Korruption behoben - "database disk image is malformed" durch kompletten FTS-Rebuild (Dec 2025).
- Sync Progress: Prozentanzeige (0-100%) für IMPORT, CHUNK, EMBED Phasen implementiert (Dec 2025).
- Bugfix: Chunking-Loop - Dokumente <100 Zeichen werden jetzt korrekt gefiltert (Dec 2025).
- Bugfix: Tabellen-Overflow - Spalten wurden bei <1200px abgeschnitten, jetzt scrollbar (Dec 2025).
- HTMX Error-States: Loading-Spinner, Toast-Notifications, Error-Container mit Retry (Dec 2025).
- Icon-Migration: Feather Icons → Lucide Inline SVGs (Jinja2-Makro) (Dec 2025).
- Bugfix: Alpine.js/Feather Icons Konflikt auf Digest-Seite behoben (Dec 2025).

- UI-Update: Hero-Suchfeld auf Startseite (Dec 2025).
- Such-Refactoring: Gruppierung nach Dokument mit Evidence-URL (Dec 2025).
- Dokumentations-Update (PROJECT_BRIEF, CLAUDE.md, DESIGN_SYSTEM).
