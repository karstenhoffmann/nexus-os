# Mission Control

## Current Phase
**Phase 1: Content MVP** (in progress)

## Active Task
DaisyUI Migration - Phase 1 Complete, Phase 2-5 Pending

## Next Steps (Priority Order)

### 1. DaisyUI Migration (4 templates remaining)

| Template | CSS Lines | Status |
|----------|-----------|--------|
| `home.html` | ~150 | ✅ DONE |
| `admin_fetch.html` | ~500 | pending |
| `admin_prompts.html` | ~500 | pending |
| `admin_queries.html` | ~350 | pending |
| `admin_compare.html` | ~150 | pending |
| `sync.html` | ~130 | pending |

**Workflow:** Preview route → Screenshot comparison → Design-audit → Implement

### 2. CSS Cleanup
- [ ] Replace custom toast in `app.css` with DaisyUI `toast`

### 3. Draft System MVP
- Revisions, parking/finalizing (after DaisyUI cleanup)

## Recent Completions
- Dec 2025: **Elevation & Visual Hierarchy system** - Three-Plane Model (Canvas/Surface/Control)
- Dec 2025: **Hero search migrated to DaisyUI** - Removed ~150 lines custom CSS
- Dec 2025: **Theme portability verified** - garden/emerald/dark all work without CSS changes
- Dec 2025: DAISY_SPECS.md Section 0 added (foundational elevation principle)
- Dec 2025: base.html canvas set to `bg-base-200` for proper elevation
- Dec 2025: Design-audit workflow operational (Playwright screenshots + rule check)
- Dec 2025: DaisyUI garden theme + dark mode toggle
- Dec 2025: Python 3.14 upgrade

## Open Questions
- Align CLAUDE.md "NO Node.js" with architecture.md "propose first" policy

## Decisions Made
| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 2025 | Elevation Principle (Section 0) | Canvas `bg-base-200`, Surfaces `bg-base-100 shadow-md`, Controls border-defined |
| Dec 2025 | One btn-primary per viewport | Card "Open" buttons use `btn-outline`, search uses `btn-primary` |
| Dec 2025 | Theme portability | All colors via DaisyUI semantic classes, no hardcoded colors |
| Dec 2025 | Playwright in design-audit | Catches rendered issues code inspection misses |
| Dec 2025 | DaisyUI "garden" theme | Clean light theme, pairs with "dark" for toggle |
