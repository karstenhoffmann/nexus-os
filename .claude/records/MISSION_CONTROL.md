# Mission Control

## Current Phase
**Phase 1: Content MVP** (in progress)

## Active Task
**Digest 2.0 Phase B: Interactive Curation** - Ready to Start

---

## Next Steps (Priority Order)

### 1. Library Page Redesign - COMPLETED
- [x] DaisyUI Filter component for category filters (checkbox-based)
- [x] DaisyUI Badge outline for table type badges
- [x] CSS fallback for badge-outline (nested CSS compatibility)
- [x] Stats bar, search card, zebra table styling

### 2. Digest 2.0 - VISION COMPLETE, READY FOR IMPLEMENTATION
**Full vision documented in:** `.claude/docs/whiteboard.md`

**Core Concept:** Digest is not an endpoint - it's a Content Workbench in a transformation pipeline:
```
Raw Content → [Lens] → Digest → [Curate] → Draft → [Format] → LinkedIn/Newsletter/Blog
```

**Implementation Phases (from whiteboard):**
- [x] **Phase A: Source Transparency** - COMPLETE (Dec 22, 2025)
- [ ] **Phase B: Interactive Curation** - Include/exclude, ratings, reorder, markers
- [ ] **Phase C: Draft Bridge** - Curated digest → format selection → draft generation
- [ ] **Phase D: Pipeline Visibility** - Real-time progress, cluster visualization
- [ ] **Phase E: Lens Foundation** - Built-in presets, lens selection
- [ ] **Phase F: Lens Editor + Preview** - Test corpus, full CRUD on all lenses
- [ ] **Phase G: Belief-Aware Lenses** - MVP profile, aligned/challenger lenses

**Key Features Designed:**
- Universal Content Actions: [Context] [Full Text] [Open in Reader] [Original ↗]
- Lens System: WHAT (scope) vs HOW (lens) separation
- Full Lens CRUD: View/Test/Edit/Clone/Delete even built-in lenses
- Interactive Curation: Include/exclude, ★★★ ratings, drag-to-reorder
- Draft Bridge: Curated selection → format → generate with your angle

**Future Vision (Phase 3+):**
- "Me as Entity" - User is special person in unified entity system
- Writing Style Engine - Hierarchical layers, learning from feedback
- Unstructured Input → Structured Extraction

### 3. Draft System MVP
- Revisions, parking/finalizing
- Will integrate with Digest 2.0 Draft Bridge

## Recent Completions
- Dec 22, 2025: **Phase A: Source Transparency COMPLETE** - Full implementation: database fixes (N+1 query, saved_at index, reader_url column), COMPILE phase wires citations to normalized tables, API endpoint `/api/digest/{id}/topics/{tid}/sources`, frontend source badges with expandable panel showing document titles, authors, excerpts, and action buttons (Full Text, Original). Verified working with digest ID 8 (293 sources).
- Dec 2025: **CLAUDE.md Context Optimization** - 77% reduction in auto-loaded context. Restructured Directory Mapping, removed dead links, fixed broken file paths. Auto-load: 436 lines (was 1,922).
- Dec 2025: **Digest 2.0 Vision Complete** - Full redesign documented in whiteboard.md (~1200 lines). Content Workbench concept, Lens system, Interactive Curation, Draft Bridge, Profile system vision.
- Dec 2025: **DaisyUI 100% Compliance** - Zero custom overrides, pure DaisyUI patterns throughout. Fixed: bg-transparent, border-0, outline-none, focus-within:* anti-patterns. Added prevention rules to CLAUDE.md.
- Dec 2025: **Library page UX redesign** - Proper DaisyUI Filter component, Badge outline for table, CSS fallback for modern nested CSS
- Dec 2025: **Admin tabs-lift with DaisyUI v5** - Label wrapper pattern with icons
- Dec 2025: **Main entry points UX redesign** - sync/drafts/digest/admin pages with hero sections, stats bars
- Dec 2025: **CSS Cleanup complete** - Custom CSS replaced with DaisyUI components, emerald theme
- Dec 2025: **All templates migrated to DaisyUI v5** - Zero custom CSS approach

## Open Questions
- Align CLAUDE.md "NO Node.js" with architecture.md "propose first" policy

## Decisions Made
| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 2025 | CLAUDE.md tiered loading | Auto-load only essential (436 lines), mention large refs like whiteboard.md (1,486 lines) |
| Dec 2025 | Digest = Content Workbench | Not a summary generator, but interactive transformation pipeline |
| Dec 2025 | WHAT vs HOW separation (Lens system) | Scope (time/sources) separate from analysis approach (prompts/style) |
| Dec 2025 | Universal Content Actions | Every content piece: [Context] [Full Text] [Open in Reader] [Original ↗] |
| Dec 2025 | Full Lens CRUD | Even built-in lenses fully transparent, viewable, testable |
| Dec 2025 | "Me as Entity" architecture | User is special person in unified entity system, not separate profile |
| Dec 2025 | Writing Style = Feature Area | Too complex for config fields, needs hierarchical engine (Phase 3+) |
| Dec 2025 | Profile MVP: flexible JSON | Don't lock schema before entity system design |
| Dec 2025 | Source Transparency first | Foundation for everything else - wire up citations before other features |
| Dec 2025 | DaisyUI Filter for category filters | Checkbox-based `btn btn-sm` pattern per official docs |
| Dec 2025 | Badge outline for table badges | `badge badge-outline badge-info` with CSS fallback |
| Dec 2025 | CSS fallback in app.css | Modern nested CSS in DaisyUI v5 needs explicit fallback |
| Dec 2025 | DaisyUI v5 tabs-lift pattern | Label wrapper with explicit text/icons |
| Dec 2025 | UX-first redesign process | Analyze purpose/flow/hierarchy BEFORE component swaps |
| Dec 2025 | State design mandatory | Empty/loading/success/error states required |
| Dec 2025 | Quick stats pattern | Key insights in `stats` bar, details below |
| Dec 2025 | Elevation Principle | Canvas `bg-base-200`, Surfaces `bg-base-100 shadow-md` |
| Dec 2025 | Theme portability | All colors via DaisyUI semantic classes only |
| Dec 2025 | Hero pattern | Title + subtitle + primary action for all entry pages |
| Dec 2025 | DaisyUI anti-patterns banned | bg-transparent, border-0, outline-none, focus-within:* on form elements break DaisyUI - added to CLAUDE.md |
