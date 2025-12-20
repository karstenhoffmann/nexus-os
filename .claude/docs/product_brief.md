# Nexus OS - Product Brief

## 10-Year Vision

A personal knowledge and network operating system for one user. Great UX working perfect on Desktop and at least ok on mobile. Built to last 10+ years: stable, cheap, low-maintenance, portable.

**Core Value Proposition:**
- Transform content consumption into actionable knowledge and output (digests, analyses, drafts)
- Query your private corpus (content + network) with semantic search
- Network as context and queryable database with history
- Work offline (read, search, write). Sync and online jobs run only with internet and manual confirmation

## Tinder Classification (Network Contacts)

Three-tier contact classification system for prioritized network enrichment:

| Tier | Name | Update Frequency | Data Collected |
|------|------|------------------|----------------|
| 1 | **Normal** | Rare updates | Basic CSV data only |
| 2 | **Aktiv** | Every 3-6 months (within caps) | CV + headline history |
| 3 | **VIP** | When economically viable | Posts + comments + full enrichment |

**Enrichment Rules:**
- Apify enrichment only for Aktiv and VIP tiers
- Update-only approach (no re-fetching unchanged data)
- Snapshots created only when changes detected
- All enrichment jobs require cost estimate + manual confirmation

## Phase Roadmap

### Phase 0: Feasibility (Foundation)
- Readwise import probe (200-500 items)
- LinkedIn CSV column and data quality check
- Apify test with 20 profiles
- **Acceptance:** Import, parser, and field stability confirmed. Costs roughly estimated.

### Phase 1: Content MVP (Daily Use)
- Import Readwise with dedupe and offline browse
- FTS search + filters
- Build embeddings, semantic search
- Saved queries and digest defaults
- Draft system: revisions, parking, finalizing, folders, tags
- **Acceptance:** Complete workflow from import to final post. Backup/restore tested.

### Phase 2: Research MVP
- Claim extraction UI
- Quick fact-check report
- Why-chain artifact
- **Acceptance:** Reports saveable and referenceable in drafts.

### Phase 3: Network MVP
- CSV import with dedupe and merge UI
- Tinder classification
- Groups and tags
- Explore Network queries + export
- **Acceptance:** 2000 contacts imported, classified, exportable.

### Phase 4: Network Enrichment
- Apify enrichment for Aktiv and VIP
- Background updates within caps
- Network digest for changes
- **Acceptance:** History visible, no unnecessary fetches, confirm-gated or capped.

## Product Modules (4 Equal Entry Points)

### 1. Explore Content (Query Workbench)
- Freetext query + simple filters
- Result views: List, Table, Timeline, Theme clusters, Narrative answer with citations
- Always show: sources, IDs, original URL

### 2. Digests (Saved Queries)
- Digest = saved query with default time range (e.g., last 7 days)
- Output: deduplicated theme clusters, key claims, source list, highlights

### 3. Writing (Draft System)
- Drafts created from: based on a Digest (can then be modified freely by emphasizing, deleting, modifying topics, adding persons or organisations and their respective context, adding own takes, stories, personal attitude, experiences, etc.), Explore, Research artifacts, Network insights
- Iterative: generate, edit, regenerate, park, finalize
- Revisions are mandatory
- Organization: folders and tags, search

### 4. Explore & Maintain Network
- Queries over persons, orgs, relationships, groups, history
- Freetext query + simple filters
- Result views: List, Table, Timeline, Clusters, Trends, narrative answers with citations
- Export results (profile URLs, names, groups)
- Add, modify, delete persons, orgs or companies
- Create/add/delete context for any entity in free text form (system extracts structured information and distributes to right places in database)

## Non-Goals (Explicit)

- Multi-user, sharing, collaboration
- Realtime streaming
- Fully automated mass scraping without caps
- Native mobile app
- Perfect style learning immediately (style evolves organically over time)

## Guardrails (Non-Negotiable)

1. **Beginner-Friendly & Teaching:** Agent is implementer and coach. Every manual action explained with why, how, success criteria, typical errors.

2. **Evidence First:** Outputs must reference sources. Prefer source_url. Clear fallback if unavailable.

3. **Additive & Versioned:** No silent overwrites. Changes create revisions or snapshots. Default view shows latest; history remains accessible.

4. **Dedupe & Merge:** No unnoticed duplicates. When detected: merge proposal. Default is lossless merge with manual correction.

5. **Cost Control, Confirm by Default:** Expensive jobs (LLM, web checks, Apify, large imports) only after manual confirmation. Every LLM job logs provider, model, parameters.

6. **Offline-First Usage:** Offline must work: browse, search, queries over local data, organization. Online only: sync, fact-checks, LLM-supported draft writing, topic clustering, embedding, deep research, Apify enrichment.

7. **Simplicity over Perfection:** No Node for backend/UI. Stack intentionally conservative, modular, replaceable.
