# Mission Control

## Current Phase
**Phase 1: Content MVP** (in progress)

## Active Task
DaisyUI Migration - COMPLETE

## Next Steps (Priority Order)

### 1. DaisyUI Migration - COMPLETED

| Template | CSS Lines | Status |
|----------|-----------|--------|
| `home.html` | ~150 | ✅ DONE |
| `sync.html` | ~130 | ✅ DONE |
| `admin_fetch.html` | ~500 | ✅ DONE |
| `admin_prompts.html` | ~315 | ✅ DONE |
| `admin_queries.html` | ~230 | ✅ DONE |
| `admin_compare.html` | ~75 | ✅ DONE (UX redesign) |

**All 6 templates migrated to DaisyUI with zero custom CSS.**

### 2. CSS Cleanup
- [ ] Replace custom toast in `app.css` with DaisyUI `toast`

### 3. Draft System MVP
- Revisions, parking/finalizing (after DaisyUI cleanup)

## Recent Completions
- Dec 2025: **UX Design System created** - New `UX_DESIGN_PRINCIPLES.md`, updated `design-audit` skill with UX-first approach
- Dec 2025: **admin_compare.html UX redesign** - Full redesign with hero search, quick stats bar, state design (empty/loading/error)
- Dec 2025: **admin_queries.html migrated** - Removed ~230 CSS lines, collapse/badges/forms to DaisyUI, creation form moved to top
- Dec 2025: **admin_prompts.html migrated** - Removed ~315 CSS lines, modal/forms/badges to DaisyUI
- Dec 2025: **admin_fetch.html migrated** - Removed ~220 CSS lines, text integrity checks added
- Dec 2025: **sync.html migrated** - Stats consolidated (5→3), custom stepper with DaisyUI variables
- Dec 2025: **Elevation & Visual Hierarchy system** - Three-Plane Model (Canvas/Surface/Control)
- Dec 2025: **Hero search + home.html migrated** - DaisyUI garden theme + dark mode toggle

## Open Questions
- Align CLAUDE.md "NO Node.js" with architecture.md "propose first" policy

## Decisions Made
| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 2025 | UX-first redesign process | Analyze purpose/flow/hierarchy BEFORE component swaps |
| Dec 2025 | State design mandatory | Empty/loading/success/error states required for interactive pages |
| Dec 2025 | Quick stats pattern | Key insights in `stats` bar, details below |
| Dec 2025 | Status info as pills | Compact inline pills, not full cards |
| Dec 2025 | Creation forms at top | "Add new X" above list of X - primary action visible without scroll |
| Dec 2025 | Text integrity check | `whitespace-nowrap` + `inline-flex` for icon+text buttons |
| Dec 2025 | Custom CSS criteria | Only when DaisyUI has no equivalent AND uses DaisyUI variables |
| Dec 2025 | Stats consolidation | 2-4 stats max, sub-metrics in `stat-desc` |
| Dec 2025 | Elevation Principle | Canvas `bg-base-200`, Surfaces `bg-base-100 shadow-md` |
| Dec 2025 | One btn-primary per viewport | Card buttons use `btn-outline`, search uses `btn-primary` |
| Dec 2025 | Theme portability | All colors via DaisyUI semantic classes only |
