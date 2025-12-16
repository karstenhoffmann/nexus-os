nexus-os

1. Zweck
   Single-User, local-first System fuer 10+ Jahre.
   Es speichert und organisiert:

- Content Inputs (Start: Readwise Reader API), inkl. Volltext, Metadaten, Highlights, Notizen, Originalquellen-URLs
- Queries (Keyword + echte semantische Suche) ueber den privaten Korpus, mit Filtern und Quellenbezug
- Digests (Default und frei definierbare Saved Queries)
- Drafts fuer eigene Texte (Start: LinkedIn-Post), iterativ, versioniert, spaeter weitere Formate
- Network (spaeter): LinkedIn Kontakte via CSV, Anreicherung via Apify, Zeitverlauf, Gruppen, Exporte

2. Nutzerprofil
   Der Mitentwickler und spaetere Nutzer sind die gleiche Person.
   Am Anfang geringe Software-Erfahrung.
   Konsequenz:

- Der Coding Agent ist Implementierer und Lehrer.
- Jeder manuelle Schritt ausserhalb des Repos wird kurz erklaert (wo, warum, wie, Erfolgskriterium).

3. Hard Constraints

- Single User
- Portabel (Laptop oder VPS), Backup und Restore sehr einfach
- Offline nutzbar fuer Browsing, Suche, Drafts, Historie (Sync und LLM benoetigen Netz)
- App-Runtime ohne Node
- SQLite als einzige DB
- Semantische Suche via sqlite-vec

4. Guardrails

- Jede grosse Aktion ist Plan -> Preview -> Confirm -> Execute
- Teure Aktionen (LLM, Scraping, viele Requests) nur nach expliziter Bestaetigung
- Keine stillen Overwrites: Versionierung und Historie
- Dedupe und Merge statt Duplikat-Chaos

5. Stack

- Backend: Python + FastAPI
- UI: server-rendered HTML (Jinja2) + HTMX + Alpine
- DB: SQLite + FTS5 + sqlite-vec
- Runtime: Docker-kompatibel (OrbStack ok)

6. Node Regel (wichtig)
   Node ist erlaubt, aber nur fuer Tooling unter tools/.
   Node wird niemals Teil der App-Runtime.
   Dockerfile installiert kein Node.
   App-Code importiert keine Node-Module.
   Wenn jemand versucht, Node in die App zu ziehen: stoppen und zurueck.

7. Epics (kurz)
   A Fundament: App laeuft, DB init, Admin Diagnose
   B Content Ingest: Readwise Preview + Confirm + Save
   C Suche: FTS + sqlite-vec Einbau, semantische Suche
   D Digests: Saved Queries, Default Digest, Claims Liste
   E Drafts: LinkedIn Post, Iterationshistorie, final markieren, Ordner, Tags
   F Network spaeter: CSV Import, Merge UI, Gruppen, Tiers, Apify Enrichment

