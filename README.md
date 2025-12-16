nexus-os

0. Kurzuebersicht

- App-Runtime: Python + FastAPI + SQLite + FTS5 + sqlite-vec, UI via HTMX + Alpine
- Tooling: Node nur in tools/ fuer Playwright MCP und optional Playwright Tests
- Daten liegen lokal unter ./_local (niemals ins Git)

1. Voraussetzungen
   WO: macOS

- OrbStack oder Docker Desktop
- Git
- Optional: Node (nur fuer Tooling)

Sanity Check
WO: Terminal, beliebiger Ordner
WARUM: prueft, ob docker und compose erreichbar sind
Befehle:
docker version
docker compose version

2. Erstes Setup
   WO: Repo Root ~/dev/nexus-os
   2.1 .env anlegen
   WARUM: lokale Konfiguration ohne Git
   Befehl:
   cp .env.example .env
   Dann Datei .env oeffnen und OPENAI_API_KEY setzen.

2.2 App starten
WARUM: lauffaehige Basis fuer alles weitere
Befehl:
docker compose up --build
Dann Browser: http://localhost:8000

2.3 App stoppen
Befehl:
docker compose down

3. Daten und Backup
   WICHTIG: Alle persoenlichen Daten liegen in ./_local.
   GitHub speichert nur Code, nicht Daten.

Backup
WO: Repo Root
WARUM: Rechnerverlust ueberleben
Befehl:
tar -czf nexus_os_local_backup_YYYYMMDD.tar.gz _local

Restore

- Repo klonen
- _local aus Backup zurueckkopieren
- .env setzen
- docker compose up --build

4. Tooling Regeln

- Node nur in tools/
- App-Runtime ohne Node
