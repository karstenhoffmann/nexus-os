# nexus-os

**Entwickler-Notiz**:

- Vision & Architektur: Siehe `PROJECT_BRIEF.md`
- UI/UX Standards: Siehe `DESIGN_SYSTEM.md`
- Aktueller Status: Siehe `STATE.md`

## 0. Kurzuebersicht

- App-Runtime: Python + FastAPI + SQLite + FTS5 + sqlite-vec, UI via HTMX + Alpine
- Tooling: Node nur in tools/ fuer Playwright MCP und optional Playwright Tests
- Daten liegen lokal unter ./_local (niemals ins Git)

## 1. Voraussetzungen

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

## 2. Erstes Setup

WO: Repo Root ~/dev/nexus-os
2.1 .env anlegen
WARUM: lokale Konfiguration ohne Git
Befehl:
cp .env.example .env
Dann Datei .env oeffnen und OPENAI_API_KEY setzen.

### 2.2 App starten

WARUM: lauffaehige Basis fuer alles weitere
Befehl:
docker compose up --build
Dann Browser: http://localhost:8000

### 2.3 App stoppen

Befehl:
docker compose down

## 3. Daten und Backup

WICHTIG: Alle persoenlichen Daten liegen in _local.
GitHub speichert nur Code, nicht Daten.

**Backup**
WO: Repo Root
WARUM: Rechnerverlust ueberleben
Befehl:
tar -czf nexus_os_local_backup_YYYYMMDD.tar.gz _local

**Restore**

- Repo klonen
- _local aus Backup zurueckkopieren
- .env setzen
- docker compose up --build

## 4. Tooling Regeln

- Node nur in tools/
- App-Runtime ohne Node

## 5. Troubleshooting

### 5.1 OpenAI API Fehler 429

WICHTIG: Zwei verschiedene 429-Fehler unterscheiden!

**"Rate limit reached":**

- Ursache: Zu viele Requests pro Minute (selten bei Embeddings)
- Loesung: Warten hilft hier

**"You exceeded your current quota":**

- Ursache: Keine Credits (OpenAI ist prepaid seit 2024!)
- Loesung: Credits kaufen auf platform.openai.com
- WICHTIG: Warten hilft hier NICHT!

**Billing pruefen:**

1. https://platform.openai.com/settings/organization/billing/overview
2. "Credit balance" muss > $0 sein
3. Nach Kauf: Ggf. neuen API Key erstellen

### 5.2 Embeddings generieren

WO: Browser http://localhost:8000/admin
WARUM: Embeddings fuer semantische Suche generieren
Kosten: ca. $0.02 pro 1000 Dokumente (text-embedding-3-small)

Oder via Script (schneller):
./scripts/generate-all-embeddings.sh

Rate Limits fuer text-embedding-3-small (Dezember 2025):

- Tier 1 (nach $5 Zahlung): 3,000 RPM, 1,000,000 TPM
- Tier 2 (nach $50): 5,000 RPM
- Bei 2600 Dokumenten: ~30 Sekunden moeglich
