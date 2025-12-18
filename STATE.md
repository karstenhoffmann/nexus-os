nexus-os Status

Stand (kurz)
- Semantische Suche funktioniert mit Chunk-Zitaten und Kontext.
- 2637 Dokumente haben Embeddings (OpenAI text-embedding-3-small).
- Provider-Abstraktion: OpenAI + Ollama Support mit Health-Checks.
- ContentFetcher: trafilatura fuer Fulltext-Extraktion von URLs.
- 2605 URLs warten auf Fulltext-Fetching.

Aktuelles Ziel
- Fulltext-Fetching (Plan: glistening-seeking-snowglobe.md)

Fertig (diese Session)
1) Sprint F1: DB-Schema (fetch_jobs, fetch_failures Tabellen)
2) Sprint F1: ContentFetcher mit trafilatura (content_fetcher.py)
3) Sprint F1: Tests mit echten URLs (16/16 bestanden)
4) Paywall/JS-Domain-Erkennung (medium.com, linkedin.com, etc.)

Naechste Schritte (Claude Code, max 3)
1) Sprint F2: FetchJobStore + DomainRateLimiter (fetch_job.py)
2) Sprint F3: API Endpoints + SSE Streaming
3) Sprint F4: Admin Fetch UI (/admin/fetch)

Offene Fragen (max 3)
- (keine aktuell)

Handoff
- ContentFetcher Test: docker compose exec app python -c "
  import asyncio
  from app.core.content_fetcher import fetch_url
  result = asyncio.run(fetch_url('https://example.com'))
  print(result)"
- Fetch Stats: db.count_documents_for_fetch()
  - 2605 URLs pending, 0 mit Fulltext, 0 failed
- Domain-Erkennung:
  - Paywall: medium.com, nytimes.com, wsj.com, etc.
  - JS Required: twitter.com, linkedin.com, instagram.com, etc.
- Neue DB-Tabellen: fetch_jobs, fetch_failures
- Neue DB-Methoden: save_fulltext(), save_fetch_failure(), get_fetch_failures()
- Alle Tests: docker compose exec app python -m pytest tests/ -v (32/32)

Wichtig: Sprint F2-F4 implementieren fuer vollstaendigen Fetch-Workflow!
