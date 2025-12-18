nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert
- UI-Verbesserungen: Tabellen, Dark Mode Toggle, Nav Active State
- Design-System mit Sekundaerfarbe erweitert

Aktuelles Ziel
- App nutzen und ggf. weitere Verbesserungen
- Optional: Orphan-Embeddings Cleanup (~1.950 verwaiste)

Naechste Schritte (Claude Code, max 3)
1) Optional: Orphan-Cleanup implementieren
2) Feature Development (Digests, Drafts)
3) Weitere UX-Verbesserungen

Handoff
- UI/UX Batch-Fix:
  - Admin 103% Bug: Query zaehlt nur noch existierende Chunks (storage.py:1232-1241)
  - Tabellen-Styling: .data-table Klasse mit Header, Hover, Responsive (app.css:519-581)
  - Sekundaerfarbe: --secondary, --secondary-hover, --secondary-light (app.css:14-17)
  - Dark Mode Toggle: Button im Nav, localStorage-Persistenz, data-theme Attribut
  - Nav Active State: .nav a.active Styling, JS setzt Klasse basierend auf URL
- Commit empfohlen

Status
- Total Chunks: 69.338
- Mit Embeddings: 69.346 (100%)
- Verwaiste Embeddings: ~1.950 (geloeschte Chunks)
