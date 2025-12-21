# Mission Control

## Current Phase
**Phase 1: Content MVP** (in progress)

## Active Task
DaisyUI Migration - 3 templates remaining

## Next Steps (Priority Order)

### 1. DaisyUI Migration (3 templates remaining)

| Template | CSS Lines | Status |
|----------|-----------|--------|
| `home.html` | ~150 | ✅ DONE |
| `sync.html` | ~130 | ✅ DONE |
| `admin_fetch.html` | ~500 | ✅ DONE |
| `admin_prompts.html` | ~500 | pending |
| `admin_queries.html` | ~350 | pending |
| `admin_compare.html` | ~150 | pending |

**Workflow:** Before tab → Design-audit → Implement preview → After tab → User approval loop → Finalize

### 2. CSS Cleanup
- [ ] Replace custom toast in `app.css` with DaisyUI `toast`

### 3. Draft System MVP
- Revisions, parking/finalizing (after DaisyUI cleanup)

## Recent Completions
- Dec 2025: **admin_fetch.html migrated** - Removed ~220 CSS lines, added text integrity checks to design-audit
- Dec 2025: **sync.html migrated** - Stats consolidated (5→3), custom stepper retained with DaisyUI variables
- Dec 2025: **DAISY_SPECS.md enhanced** - Integrated status pattern, stats consolidation principle, custom CSS criteria
- Dec 2025: **Design-audit workflow refined** - Two-tab Playwright comparison with explicit approval gate
- Dec 2025: **Elevation & Visual Hierarchy system** - Three-Plane Model (Canvas/Surface/Control)
- Dec 2025: **Hero search migrated to DaisyUI** - Removed ~150 lines custom CSS
- Dec 2025: DaisyUI garden theme + dark mode toggle

## Open Questions
- Align CLAUDE.md "NO Node.js" with architecture.md "propose first" policy

## Decisions Made
| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 2025 | Text integrity check in design-audit | `whitespace-nowrap` + `inline-flex` for icon+text buttons to prevent line breaks |
| Dec 2025 | Custom CSS criteria | Justified only when DaisyUI has no equivalent AND uses DaisyUI variables |
| Dec 2025 | Stats consolidation | 2-4 stats max, sub-metrics in `stat-desc`, not separate stats |
| Dec 2025 | Elevation Principle (Section 0) | Canvas `bg-base-200`, Surfaces `bg-base-100 shadow-md`, Controls border-defined |
| Dec 2025 | One btn-primary per viewport | Card "Open" buttons use `btn-outline`, search uses `btn-primary` |
| Dec 2025 | Theme portability | All colors via DaisyUI semantic classes, no hardcoded colors |
| Dec 2025 | Playwright in design-audit | Catches rendered issues code inspection misses |
| Dec 2025 | DaisyUI "garden" theme | Clean light theme, pairs with "dark" for toggle |
