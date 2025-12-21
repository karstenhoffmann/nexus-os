# Mission Control

## Current Phase
**Phase 1: Content MVP** (in progress)

## Active Task
None - ready for next task

## Next Steps (Priority Order)

### 1. DaisyUI Migration - COMPLETED
All templates migrated to DaisyUI v5 with zero custom CSS.

### 2. CSS Cleanup - COMPLETED
- [x] Replace custom toast in `app.css` with DaisyUI `toast`

### 3. Main Entry Points UX Redesign - COMPLETED
- [x] `/sync` - Action-First pattern, DaisyUI steps, help collapsed
- [x] `/drafts` - Stats bar, join filters, hero section
- [x] `/digest` - Compact generation form, inline stats+filter
- [x] `/admin` - Tabbed navigation with DaisyUI v5 tabs-lift

### 4. Draft System MVP
- Revisions, parking/finalizing (after DaisyUI cleanup)

## Recent Completions
- Dec 2025: **Admin tabs-lift with DaisyUI v5** - Fixed CDN path (v5 uses daisyui.css not dist/full.min.css), label wrapper pattern with icons
- Dec 2025: **Main entry points UX redesign** - sync/drafts/digest pages with hero sections, stats bars, Action-First pattern
- Dec 2025: **CSS Cleanup complete** - Custom toast/error CSS replaced with DaisyUI toast+alert, theme switched to emerald
- Dec 2025: **UX Design System created** - New `UX_DESIGN_PRINCIPLES.md`, updated `design-audit` skill with UX-first approach
- Dec 2025: **admin_compare.html UX redesign** - Full redesign with hero search, quick stats bar, state design
- Dec 2025: **All admin templates migrated** - queries, prompts, fetch pages converted to DaisyUI

## Open Questions
- Align CLAUDE.md "NO Node.js" with architecture.md "propose first" policy

## Decisions Made
| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 2025 | DaisyUI v5 tabs-lift pattern | Label wrapper with explicit text/icons for tab visibility |
| Dec 2025 | UX-first redesign process | Analyze purpose/flow/hierarchy BEFORE component swaps |
| Dec 2025 | State design mandatory | Empty/loading/success/error states required for interactive pages |
| Dec 2025 | Quick stats pattern | Key insights in `stats` bar, details below |
| Dec 2025 | Creation forms at top | "Add new X" above list of X - primary action visible without scroll |
| Dec 2025 | Text integrity check | `whitespace-nowrap` + `inline-flex` for icon+text buttons |
| Dec 2025 | Elevation Principle | Canvas `bg-base-200`, Surfaces `bg-base-100 shadow-md` |
| Dec 2025 | One btn-primary per viewport | Card buttons use `btn-outline`, search uses `btn-primary` |
| Dec 2025 | Theme portability | All colors via DaisyUI semantic classes only |
| Dec 2025 | Filter buttons use join+btn-active | No multiple btn-primary, use `join` with `btn-active` |
| Dec 2025 | Hero pattern | Title + subtitle + primary action in flex row for all entry pages |
