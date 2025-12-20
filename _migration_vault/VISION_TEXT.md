# Personal Knowledge + Network OS

Single User, local-first, Docker, 10+ Jahre, semantische Suche, Query-Workbench, Digests, Drafts, Network

## 1. Kontext und Ziel

Dieses Projekt baut ein persoenliches System fuer genau eine Person. Diese Person ist gleichzeitig:

- Mitentwickler (anfangs wenig Software-Erfahrung)
- spaeterer Nutzer (immer die gleiche Person)

Das System soll ueber viele Jahre stabil, billig, wartungsarm und portabel bleiben.

Hauptnutzen:

- Aus Content-Konsum wird schnell nutzbares Wissen und Output (Digests, Analysen, eigene Texte).
- Beliebige Queries an den privaten Korpus (Content und Network, auch kombiniert).
- Netzwerk als Kontext und als eigene abfragbare Datenbasis, inkl. Historie.
- Offline arbeiten koennen (lesen, suchen, schreiben). Sync und Online-Jobs laufen nur bei Internet und standardmaessig nur nach manueller Bestaetigung.

## 2. Scope und Nicht-Ziele

Im Scope:

- Content Import (Start: Readwise Reader API)
- Offline Korpus (Volltext, Metadaten, Highlights, Notes, Provenienz)
- Suche: Volltext und echte semantische Suche
- Query Workbench (Content und Network)
- Saved Queries und Digests (Digest ist nur eine Saved Query mit Default-Zeitraum)
- Draft System fuer eigene Texte (Start: LinkedIn-Post) mit Iterationshistorie, Parken, Finalisieren, Ordnern, Tags
- Research Tools als Jobs: Claim Extraktion, Quick Fact Check, Deep Fact Check, Why-Chain
- Network: LinkedIn Connections CSV Import, manuelle Kontakte, Gruppen, Tags, Tinder-Klassifizierung (Normal, Aktiv, VIP)
- Network Enrichment: Apify fuer Aktiv und VIP (sparsam, cached, update-only), Historie

Nicht-Ziele vorerst:

- Multi-User, Sharing, Kollaboration
- Realtime Streaming
- Vollautomatisches unbeaufsichtigtes Massenscraping ohne Caps
- Mobile App
- Perfektes Stil-Lernen sofort (Stil wird organisch ueber Zeit mit echten Beispielen und Revisionen)

## 3. Unverhandelbare Prinzipien (Guardrails)

### 3.1 Einsteigerfreundlich und lehrend

Der Coding Agent ist Implementierer und Coach.
Jede manuelle Aktion ausserhalb des Repos muss erklaert werden:

- Zweck (warum)
- Befehl (wie)
- Erfolgskriterium (woran erkenne ich es)
- 1 bis 2 typische Fehler und was dann zu tun ist

### 3.2 Evidence first

- Outputs muessen auf Quellen im Korpus verweisen koennen.
- Immer Originalquelle source_url bevorzugen, falls vorhanden.
- Wenn source_url fehlt oder unzuverlaessig ist: klarer Fallback (Provider-Link, Import-Provenienz).

### 3.3 Additiv und versioniert

- Keine stillen Ueberschreibungen fuer wichtige Felder.
- Aenderungen erzeugen Revisionen oder Snapshots.
- Default Ansicht zeigt immer den aktuellsten Stand, Historie bleibt abrufbar.

### 3.4 Dedupe und Merge statt Datenchaos

- Inhalte oder Kontakte duerfen nicht unbemerkt doppelt entstehen.
- Wenn doppelt: Merge-Vorschlag. Default ist verlustfrei zusammenfuehren, mit manueller Korrektur.

### 3.5 Kostenkontrolle, Confirm by default

- Teure Jobs (LLM, Web-Checks, Apify, grosse Imports) nur nach manueller Bestaetigung.
- Spaeter: Admin Panel fuer Default-Verhalten und Caps pro Tag, Woche, Monat.
  Ergaenzung:
- Jeder LLM-Job muss provider, model und zentrale Parameter loggen, damit Ergebnisse nachvollziehbar bleiben.
- Defaults sind konservativ. Teurere Modi nur nach Confirm.

### 3.6 Offline-first Nutzung

- Offline muss funktionieren: Browse, Suche, Queries ueber lokale Daten, Draft schreiben, Revisionen, Organisation.
- Online only: Sync, Fact-Checks, Deep Research, Apify Enrichment.

### 3.7 Einfachheit vor Perfektion

- Kein Node fuer Backend und UI.
- Stack bewusst konservativ, modular, austauschbar.
- Dokumente clean halten, keine Redundanz, keine widerspruechlichen Plan-Dateien.

## 4. Tech-Entscheidungen (explizit, begruendet)

### 4.1 Backend und UI

- Backend: Python 3.12, FastAPI
- UI: server-rendered HTML (Jinja2) + HTMX (partial updates) + Alpine.js (leichte Reaktivitaet)
  Begruendung:
- Modernes UX ohne SPA Build-Overhead.
- Einsteigerfreundlich, weniger moving parts, langfristig robust.

### 4.2 Datenbank und Suche

- DB: SQLite als System of Record (eine Datei)
- Volltext: SQLite FTS5
- Semantische Suche: sqlite-vec als SQLite Extension
  Begruendung:
- Portabel, Backups extrem einfach, keine extra Server.
- Semantische Suche ist Pflicht, sqlite-vec liefert das ohne externe Infrastruktur.
  Risiko:
- sqlite-vec ist pre-v1 und kann breaking changes haben.
  Mitigation:
- VectorStore Abstraktion einbauen, damit spaeter ein Wechsel moeglich ist, ohne das System umzubauen.

### 4.3 Betrieb

- Docker Compose ist Pflicht (lokal und VPS identisch).
- Daten liegen nicht im Container Write-Layer, sondern in einem Host-mount ./data.
  Begruendung:
- Reproduzierbarkeit, einfache Wiederherstellung nach Rechnerverlust.
- Kontrollierter Build der sqlite-vec Extension im Image.

### 4.4 Provider (LLM, Embeddings, Research)

Grundsatz:

- Von Anfang an eine Provider-Abstraktion bauen, damit ein Wechsel spaeter leicht ist.
- Trotzdem starten wir aus Einfachheit und Stabilitaet mit der offiziellen OpenAI API als Default.

Warum nicht sofort OpenRouter als Default:

- OpenRouter kann sehr praktisch sein (ein Key, viele Modelle, auch Embeddings).
- Fuer ein Einsteigerprojekt ist ein direkter Provider als Start oft besser:
  - weniger moving parts
  - klareres Debugging
  - weniger Abhaengigkeit von Credits, Billing-Mechaniken oder Routing-Konfiguration
- Der Code bleibt so gebaut, dass OpenRouter spaeter per Konfiguration als Provider aktiviert werden kann.

Provider-Abstraktion (muss von Beginn an existieren):

- LLMClient: Textgenerierung, Zusammenfassen, Clustering, Drafts
- EmbeddingsClient: Embeddings Erzeugung
- Optional spaeter: WebResearchClient oder Online-Mode als eigener Job-Typ

Konfiguration:

- .env steuert Provider und Keys.
- Default in v1:
  - LLM_PROVIDER=openai
  - EMBEDDINGS_PROVIDER=openai
  - OPENAI_API_KEY=...
  - Default Modelle werden zentral in einer config Datei gepinnt, nicht im Code verstreut.

Guardrails:

1. Modell-Pinning pro Job

- Jeder Job speichert provider und model.
- Modelle werden nicht still automatisch gewechselt.

2. Fallback ohne Datenmigration

- spaeterer Wechsel (OpenRouter, Anthropic, Mistral etc.) ist ein Config-Change.
- Embeddings sind provider-spezifisch und werden versioniert. Neue Embeddings koennen parallel entstehen. Alte bleiben erhalten.

3. Deep Research nicht als Black Box

- Auch wenn spaeter Modelle oder Anbieter "deep research in einem call" bieten:
  - unsere Fact-Check und Research Artefakte bleiben transparent
  - Claims, Quellenliste, Unsicherheit sind Pflicht
  - Ausfuehrung bleibt confirm-gated

## 5. Produktmodule und Einstiegsseiten

Es gibt 4 gleichwertige Einstiegspunkte. Keiner ist nur "Nebensache".

### 5.1 Explore Content (Query Workbench)

- Freitext Query plus einfache Filter.
- Ergebnis Views:
  - Liste, Tabelle, Timeline
  - optional: Themencluster
  - narrative Antwort mit Zitaten
- Immer: Quellen, IDs, Originalquelle.

### 5.2 Digests (Saved Queries)

- Digest ist eine Saved Query mit Default-Zeitraum, z.B. letzte 7 Tage.
- Ausgabe: Themencluster dedupliziert, Kernaussagen, Quellenliste, Highlights.

### 5.3 Writing (Draft System)

- Drafts entstehen aus: Digest, Explore, Research Artefakten, Network Insights.
- Iterativ: generieren, editieren, neu generieren, parken, finalisieren.
- Revisionen sind Pflicht.
- Organisation: Ordner und Tags, Suche.

### 5.4 Explore Network (Query Workbench)

- Queries ueber Personen, Orgs, Beziehungen, Gruppen, Historie.
- Export von Ergebnissen (z.B. Profil-URLs, Namen, Gruppen).

## 6. Datenmodell auf hoher Ebene (konzeptionell)

Hinweis: bewusst minimal und stabil, nicht das komplette Schema.

### 6.1 Content

- content_item: interne ID, provider, provider_item_id, source_url, provider_url, title, author, published_at, saved_at, content_type, text_plain optional, html_content optional, raw_json, current_revision_id
- content_revision: revision_id, content_item_id, created_at, payload fields
- highlight_or_note: internal_id, parent_content_item_id, kind, text, created_at, location, raw_json

### 6.2 Embeddings und Suche

Embeddings fuer:

- content chunks
- highlights
- drafts (revisionen und final)
- optional: person summaries
  VectorStore API:
- upsert, search top_k, delete by object_id

### 6.3 Drafts

- draft: draft_id, channel linkedin, type linkedin_post, subtype spaeter, status, folder_id, tags, created_at, updated_at
- draft_revision: revision_id, draft_id, created_at, text, references, user_feedback optional

### 6.4 Network

- person: person_id, canonical_key, linkedin_url optional, email optional, current_snapshot_id
- person_snapshot: snapshot_id, person_id, captured_at, source csv oder apify oder manual, headline, about, location, experience_json usw.
- organization und organization_snapshot analog
- relationship: type works_at, knows, project_role, subsidiary_of usw. plus evidence

### 6.5 Gruppen und Tags

- groups (hierarchisch moeglich)
- group_memberships (multi-membership)
- tags (frei)
- tag_assignments (drafts, persons, content usw.)

### 6.6 Jobs

- job: job_id, type, state, cost_estimate optional, requires_confirm bool, payload_json
- job_run: logs, timestamps, outputs

## 7. Semantische Suche (realistisch)

Zwei Ebenen:

- strukturiert: SQL Filter, deterministisch
- semantisch: Embedding Suche fuer aehnliche Inhalte und Passagen
  UI und Query Engine kombinieren beides, ohne heimliche LLM Entscheidungen.

## 8. Research Tools (Jobs, confirm-gated)

- Claim Extraktion: listet Claims (ohne Web Zugriff)
- Fact Check:
  - Quick: wenige Quellen, wenig Tiefe
  - Deep: mehr Quellen, mehr Checks
    Outputs: Report mit claim status, Quellen, Zitaten, Unsicherheit.
- Why-Chain: Nutzer waehlt Kernaussage und Tiefe N, Ergebnis als Artefakt.

## 9. LinkedIn und Network: kontrolliert

- Basis: LinkedIn Connections CSV Import (Stammdaten, Identitaeten).
- Tinder Klassifizierung:
  - Normal: seltene Updates
  - Aktiv: CV und Headline Historie, Updates 3 bis 6 Monate innerhalb Caps
  - VIP: zusaetzlich Posts und Kommentare, nur wenn wirtschaftlich
- Apify Enrichment:
  - nur Aktiv und VIP
  - update-only, cached
  - Snapshot nur wenn Aenderungen
  - Jobs mit Kosten Schaetzung, Confirm by default

## 10. Betrieb, Backup, Restore

- Persistente Daten in ./data auf dem Host.
- Backup ist Kopie von ./data.
- GitHub enthaelt nur Code, keine Daten.
- Restore: repo klonen, ./data zurueckkopieren, .env setzen, docker compose up.
  Ziel: unter 30 Minuten wieder arbeitsfaehig.

## 11. Phasenplan mit Akzeptanztests

Phase 0: Machbarkeit (klein, aber entscheidend)

- Readwise Importprobe (200 bis 500 Items)
- LinkedIn CSV Spalten und Datenqualitaet pruefen
- Apify Test mit 20 Profilen
  Akzeptanz: Import, Parser und Feldstabilitaet sind klar, Kosten grob abschaetzbar.

Phase 1: Content MVP (sofort nutzbar)

- Import Readwise, dedupe, offline browse
- FTS Suche plus Filter
- Embeddings bauen, semantische Suche
- Saved Queries und Digest Default
- Draft System: Revisionen, Parken, Finalisieren, Ordner, Tags
  Akzeptanz: komplette Routine Import bis finaler Post, plus Backup und Restore getestet.

Phase 2: Research MVP

- Claim Extraktion UI
- Quick Fact Check Report
- Why-Chain Artefakt
  Akzeptanz: Reports sind speicherbar und in Draft referenzierbar.

Phase 3: Network MVP

- CSV Import, dedupe und merge UI
- Tinder Klassifizierung
- Gruppen und Tags
- Explore Network Queries plus Export
  Akzeptanz: 2000 Kontakte importiert, klassifiziert, exportierbar.

Phase 4: Network Enrichment

- Apify Enrichment Aktiv und VIP
- Background Updates innerhalb Caps
- Network Digest Aenderungen
  Akzeptanz: Historie sichtbar, keine unnoetigen Abrufe, confirm-gated oder capped.

## 12. Testing Strategie

Prioritaet: Datenintegritaet und Wiederherstellbarkeit.

- Unit: dedupe keys, URL Normalisierung, snapshot change detection
- Integration: Readwise fixtures, CSV fixtures, Apify fixtures
- Smoke: start, import, search, digest, draft, backup, restore

## 13. Dokumente und Drift-Vermeidung

Single source of truth:

- PROJECT_BRIEF.md: Produkt und Architektur Wahrheit
- CLAUDE.md: Agent Regeln, ultra-kurz
- README.md: Setup und Betrieb fuer Einsteiger
- STATE.md: aktueller Stand, ToDos, offene Fragen

Regeln:

- Keine weiteren Plan-Dateien ohne klaren Bedarf.
- Keine doppelten Regeln in mehreren Dateien.
- Obsoletes wird geloescht oder konsolidiert.
- Bei Aenderungen: richtige Datei aktualisieren, nicht neue Parallel-Doku schreiben.

## 14. Naechster Schritt (immer)

Der Agent startet nicht mit grossen Features.
Erst repo skeleton, dann Phase 0 Machbarkeit.
Der aktuelle naechste Schritt steht immer in STATE.md.
