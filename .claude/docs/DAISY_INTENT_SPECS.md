# Nexus OS: Quick Intent Mapping

> Fast lookup table for Claude Code.
> **UX-FIRST:** Read `UX_DESIGN_PRINCIPLES.md` BEFORE any redesign.
> Component details: `DAISY_SPECS.md`

## Status & Feedback

| I want to show... | Use this |
|-------------------|----------|
| "Ready" / "Complete" | `badge badge-success` |
| "In Progress" | `badge badge-warning` + optional `loading loading-spinner` |
| "Error" / "Failed" | `badge badge-error` |
| Persistent ready state on card | `indicator` + `indicator-item badge badge-success` |
| Important warning (rare) | `alert alert-warning` (ONE LINE only) |
| Explanatory content | `collapse collapse-arrow` (default CLOSED) |
| Temporary notification | `toast` (auto-dismiss) |

## Data Display

| I want to show... | Use this |
|-------------------|----------|
| Key metrics (2-4) | `stats` + `stat` items |
| Data list/table | `table table-zebra table-pin-rows` |
| Process steps | `steps` + `step step-primary` |
| History/events | `timeline` |
| Progress bar | `progress progress-primary` |
| Expandable details | `collapse collapse-arrow` |

## Actions & Navigation

| I want to... | Use this |
|--------------|----------|
| Primary action | `btn btn-primary` (ONE per viewport) |
| Secondary action | `btn btn-outline` |
| Subtle/cancel action | `btn btn-ghost` |
| Dangerous action | `btn btn-error` |
| Group related buttons | `join` + `join-item` |
| Page tabs | `tabs tabs-bordered` |
| Breadcrumb trail | `breadcrumbs` |
| Pagination | `join` with btn items |

## Forms

| I want to... | Use this |
|--------------|----------|
| Text input | `input input-bordered` in `form-control` |
| Long text | `textarea textarea-bordered` |
| Dropdown | `select select-bordered` |
| On/off toggle | `toggle` |
| Checkbox option | `checkbox` |
| Show validation error | `input-error` + `text-error` helper |

## Layout

| I need... | Use this |
|-----------|----------|
| Page grid | `grid grid-cols-1 md:grid-cols-12 gap-6` |
| Card container | `card bg-base-100 shadow` |
| Card content | `card-body` + `card-title` |
| Card actions | `card-actions justify-end` |
| Section divider | `divider` (sparingly) |
| Sidebar layout | Main: `md:col-span-8`, Side: `md:col-span-4` |

## Color Rules (The 90% Rule + Elevation)

| Purpose | Color class |
|---------|-------------|
| Page canvas | `bg-base-200` |
| Surfaces (cards, forms) | `bg-base-100` + `shadow-md` |
| Nested/inset areas | `bg-base-200/50` |
| Primary text | `text-base-content` |
| Secondary text | `text-base-content/60` |
| Muted text | `text-base-content/40` |
| Borders | `border-base-300` |

**Elevation:** Canvas (`base-200`) → Surface (`base-100` + shadow) → Controls (borders, not bg)

## Page Structure Rules

| Principle | Rule |
|-----------|------|
| Creation at top | "Add new X" forms/buttons go ABOVE the list of X items, never below |
| Primary action visible | Main action accessible without scrolling (hero position) |
| Read-heavy pages | List/browse content below creation actions |
| Results near action | Feedback appears close to triggering element |
| Secondary info compact | Status/context as pills or badges, not cards |
| Help de-prioritized | Hints/help in `collapse`, default closed, bottom of page |

## State Design (MANDATORY for interactive pages)

| State | Pattern | Notes |
|-------|---------|-------|
| Empty | Emoji + guiding text, centered | Never leave blank |
| Loading | `loading loading-spinner` + skeleton | Show progress |
| Success | Results with `x-transition` animation | Celebrate completion |
| Error | `alert alert-error` + recovery button | Clear next step |

## Visual Hierarchy Rules

| Priority | Visual Weight | Examples |
|----------|---------------|----------|
| 1 (Primary) | Largest, top position, primary color | Hero action, key metric |
| 2 (Supporting) | Medium, near primary | Results, confirmation |
| 3 (Context) | Compact, inline | Status badges, pills |
| 4 (Reference) | Collapsed, bottom | Help, hints, details |

## Anti-Patterns (NEVER)

### Component Anti-Patterns
- Large `bg-primary/secondary/accent` panels
- Multiple `btn-primary` in same view
- `alert` for non-urgent information
- Tailwind colors like `bg-blue-500`
- Nested cards (card inside card)
- `btn-xs` for primary actions
- Creation forms at bottom of lists (forces scroll to act)

### UX Anti-Patterns
- Primary action below the fold (requires scroll to act)
- Results/feedback far from triggering action
- Status info in full cards (should be pills/badges)
- Help/hints always expanded (should be collapsed)
- No empty state (blank area is confusing)
- No loading feedback (user unsure if action worked)
- Same visual weight on all elements (nothing stands out)
