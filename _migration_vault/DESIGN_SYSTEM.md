# Nexus OS Design System

## Prinzipien

- **Offline-First**: Alle UI-Elemente müssen ohne Internet laden.
- **Pragmatismus**: Nutze Tailwind-Standardklassen. Keine custom CSS-Tricks ohne Not.
- **Evidence-First**: Jede Datenansicht muss `source_url` anzeigen (Herkunft).

## Komponenten-Standards (DoD)

- **Buttons**: Müssen einen `disabled`-State während HTMX-Requests haben.
- **Listen**: Große Listen brauchen serverseitiges Paging (FastAPI/SQL-Limit).
- **Fehler**: Jeder API-Call braucht einen Error-State in der UI.
- **Suchergebnisse**: Gruppiert nach Dokument (keine Chunk-Duplikate), mit Preview.

## Referenz-Struktur

Niemals von diesem HTML-Grundgerüst abweichen:

- Header: Navigation & Suche
- Main: Fokus-Inhalt (Card-basiert)
- Sidebar (Optional): Metadaten & Links

## Qualitätssicherung

Neue UI-Features werden via Playwright MCP auditiert. Scripts in `tests/e2e/`.
