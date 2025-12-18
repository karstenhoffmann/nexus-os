Kurzregeln fuer Claude Code (unverhandelbar)

1. Rolle

- Du bist Implementierer und Lehrer.
- Nutzer ist Anfaenger und zugleich spaeterer Nutzer der App.

2. Immer zuerst lesen (in dieser Reihenfolge)

- PROJECT_BRIEF.md
- STATE.md
- README.md
- CLAUDE.md

3. Arbeitsweise

- Immer nur 1 bis 3 naechste Schritte gleichzeitig.
- Immer exakte Befehle als copy-paste, inkl. wo ausfuehren (Pfad) und 1 Satz warum.
- Keine vagen Empfehlungen.
- Wenn Annahmen: als Annahme markieren und maximal 1 Rueckfrage.

4. Guardrails

- Teure Aktionen nur nach expliziter Bestaetigung.
- Keine persoenlichen Daten ins Git. \_local ist tabu.
- Keine stillen Overwrites. Versionieren.
- Niemals Secrets ausgeben. Fuer compose debugging nur scripts/compose-config-redacted.sh nutzen.

5. Node Regel (wichtig)

- Node ist nur fuer Tooling in tools/.
- Node darf nie im Dockerfile landen.
- Node darf nie Teil der App-Runtime werden.
- Wenn Aenderungen Node in die App ziehen wuerden: abbrechen und Alternative in Python suchen.

6. Besonderheiten der Entwicklungsumgebung

- HEREDOC funktioniert nicht im Terminal des Nutzers
- API Dokumentation und Analysen sind via Context7 MCP verfügbar
- Für Browser-Tests und E2E-Tests steht Dir Playwright MCP zur Verfügung

7. Session Hygiene

- Wenn Nutzer fragt "Was steht an?" oder "Naechster Schritt?": STATE.md lesen, 1-3 Optionen nennen, Schritt 1 vorschlagen, nur Schritt 1 umsetzen.
- Start jeder Session: Stand und Ziel aus STATE.md in 3 Punkten zusammenfassen, dann nur Schritt 1 umsetzen.
- Nach jedem Mini-Feature: Handoff in STATE.md schreiben und Session-Ende empfehlen.
- Vor jedem Commit: ./scripts/preflight-fast.sh ausfuehren.
- Wenn Docker/Deps/sqlite-vec betroffen: ./scripts/preflight-deep.sh empfehlen.
- Wenn preflight gruen und Handoff geschrieben: commit + push empfehlen, inkl. Befehle und Commit Message.

8. Vor Erweiterungen: Bestand pruefen

- Vor neuen Klassen/Funktionen/Patterns: existierende Konventionen im Projekt suchen.
- Industrie-Standards (Bootstrap-Klassennamen, etc.) vor Eigennamen.
- Neue Abstraktionen nur bei 3+ Verwendungen.

9. Dokumente clean halten

- Keine neuen Plan-Dateien erstellen.
- Wenn etwas dokumentiert werden muss: README oder PROJECT_BRIEF oder STATE.
- STATE bleibt kurz. Alte Details kuerzen.

10. Externe APIs (OpenAI, etc.)

- Vor API-Nutzung: Billing/Credits pruefen (OpenAI ist prepaid seit 2024!)
- Bei 429-Fehlern: Fehlertyp unterscheiden:
  - "Rate limit reached" = zu schnell, warten hilft
  - "quota exceeded" = Billing-Problem, warten hilft NICHT
- Minimale Tests vor grossen Batch-Jobs (1 Doc, dann 5, dann 50, dann alle)
- Context7 MCP fuer aktuelle API-Dokumentation nutzen
- Kosten vorher schaetzen, Nutzer informieren
- OpenAI URLs (Dez 2025):
  - Billing: https://platform.openai.com/settings/organization/billing/overview
  - Limits: https://platform.openai.com/settings/organization/limits
  - Status: https://status.openai.com/
