# daisyUI Design System (Nexus OS v2025)

> Comprehensive component mapping and design rules for Claude Code.

## Core Philosophy

**Design Through Constraint:**
DaisyUI provides semantic components that enforce consistency. Our job is to:
1. Map user intent to the RIGHT component
2. Use semantic colors that work across themes
3. **Maintain visual hierarchy through elevation**
4. Follow structural patterns from PAGE_TEMPLATES.md

**The 90% Rule:**
- 90% of UI should be neutral (base-100, base-200, base-content)
- Color is reserved for: interactive elements, status indicators, focus states
- Large colored blocks are FORBIDDEN

**The Elevation Principle:**
Every interface has visual depth. Elements must have clear contrast with their container to be perceivable and feel interactive.

---

## 0. Elevation & Visual Hierarchy (FOUNDATIONAL)

This section defines the visual "physics" of the UI. All other rules build on this.

### The Three-Plane Model

```
┌──────────────────────────────────────────────────┐
│  CANVAS (page background)                        │
│  ┌──────────────────────────────────────────┐    │
│  │  SURFACE (cards, forms, search bars)     │    │
│  │  ┌──────────────────────────────────┐    │    │
│  │  │  CONTROLS (inputs, buttons)      │    │    │
│  │  └──────────────────────────────────┘    │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

| Plane | Purpose | Treatment | DaisyUI Classes |
|-------|---------|-----------|-----------------|
| **Canvas** | Page background, recessed | Darker neutral | `bg-base-200` |
| **Surface** | Interactive containers | Lighter + shadow | `bg-base-100 shadow-md` |
| **Control** | Inputs within surfaces | Integrated, bordered | `input-bordered` (no bg change) |

### Contrast Rules

**Canvas → Surface (MUST be distinct):**
- Surfaces sit ON the canvas like paper on a desk
- Achieved via: brightness difference (`base-200` → `base-100`) + shadow
- Minimum shadow: `shadow-md` for cards, `shadow-lg` for hero elements

**Surface → Control (MUST be harmonious):**
- Controls integrate INTO the surface, not fight against it
- Inputs defined by BORDERS, not background color differences
- Avoid stark internal contrast (no `bg-base-200` inside white containers)
- Select/dropdown: same background as container, rely on border/arrow for affordance

**Control → Emphasis (Color is the exception):**
- ONE `btn-primary` per viewport for the main action
- Focus states add color ring, not background change
- Status badges use color; surrounding UI does not

### Implementation

**base.html setup:**
```html
<body class="bg-base-200">
  <main class="...">
    <!-- All content sits on base-200 canvas -->
  </main>
</body>
```

**Surface pattern (cards, forms, search bars):**
```html
<div class="bg-base-100 shadow-md rounded-lg">
  <!-- Content with harmonious internal contrast -->
</div>
```

**Control pattern (inputs inside surfaces):**
```html
<!-- Inside a bg-base-100 surface -->
<input class="input input-bordered bg-transparent" />
<select class="select select-bordered bg-transparent" />
```

### Anti-Patterns (Elevation Crimes)

| Crime | Why It's Wrong | Fix |
|-------|---------------|-----|
| Same bg for page and cards | No elevation, flat appearance | Page: `bg-base-200`, Cards: `bg-base-100` |
| Stark bg difference inside container | Visual discord, harsh internal contrast | Use borders, not backgrounds |
| Shadow without brightness difference | Floating grey on grey | Ensure `base-100` on `base-200` |
| Custom bg colors (`bg-gray-100`) | Breaks theme consistency | Use only `base-*` semantic colors |

### Audit Checklist (Elevation)

- [ ] Page/body has `bg-base-200`
- [ ] All cards/surfaces have `bg-base-100 shadow-md`
- [ ] No background color differences within a single surface
- [ ] Inputs use `input-bordered`, not custom backgrounds
- [ ] Clear visual lift between canvas and surfaces at 375px AND 1200px

---

## 1. Intent-to-Component Mapping

### Status & Feedback

| User Intent | Component | Example |
|-------------|-----------|---------|
| "Show completion" | `badge badge-success` | `<span class="badge badge-success">Done</span>` |
| "Show in-progress" | `badge badge-warning` | `<span class="badge badge-warning">Processing</span>` |
| "Show error" | `badge badge-error` | `<span class="badge badge-error">Failed</span>` |
| "Persistent success state" | `indicator` + `badge` | See below |
| "Ephemeral notification" | `toast` | Auto-dismiss after 3s |
| "Important warning" | `alert alert-warning` (SMALL) | One-liner only |
| "Explanatory info" | `collapse collapse-arrow` | Default CLOSED |

**Indicator Pattern (for "Ready" states):**
```html
<div class="indicator">
  <span class="indicator-item badge badge-success"></span>
  <div class="card">...</div>
</div>
```

### Data Display

| User Intent | Component | Notes |
|-------------|-----------|-------|
| "Show key metrics" | `stats` | 2-4 items max, horizontal on desktop |
| "Show data list" | `table table-zebra` | Pin rows for long lists |
| "Show steps" | `steps` | Horizontal, max 5 steps |
| "Show timeline" | `timeline` | Vertical, for history |
| "Show card grid" | `card` in `grid` | Use col-span rules |
| "Expandable details" | `collapse` | Default closed |

### Navigation & Actions

| User Intent | Component | Notes |
|-------------|-----------|-------|
| "Primary action" | `btn btn-primary` | One per visible area |
| "Secondary action" | `btn btn-outline` | Multiple allowed |
| "Tertiary action" | `btn btn-ghost` | Subtle, for less important |
| "Group buttons" | `join` | Connected buttons |
| "Page navigation" | `pagination` or `join` | At bottom of lists |
| "Tab switching" | `tabs tabs-bordered` | Max 5 tabs |
| "Breadcrumb path" | `breadcrumbs` | Detail pages only |

### Forms & Input

| User Intent | Component | Notes |
|-------------|-----------|-------|
| "Text input" | `input input-bordered` | Always bordered |
| "Long text" | `textarea textarea-bordered` | With rows attribute |
| "Selection" | `select select-bordered` | Always bordered |
| "Toggle option" | `toggle` or `checkbox` | Toggle for on/off |
| "Field with label" | `form-control` + `label` | ALWAYS use structure |
| "Validation state" | `input-error`, `input-success` | With helper text |

**Form Control Pattern:**
```html
<div class="form-control">
  <label class="label">
    <span class="label-text">Field Name</span>
  </label>
  <input type="text" class="input input-bordered" />
  <label class="label">
    <span class="label-text-alt text-base-content/50">Helper text</span>
  </label>
</div>
```

---

## 2. Semantic Color System

### Backgrounds (follows Elevation Principle from Section 0)

| Use Case | Class | When to Use |
|----------|-------|-------------|
| Page canvas | `bg-base-200` | Body/main background |
| Surfaces (cards, forms) | `bg-base-100` | All elevated containers |
| Nested/inset areas | `bg-base-200/50` | Inside surfaces for grouping |
| Stripe pattern | `bg-base-200/30` | Alternating table rows |

**FORBIDDEN:**
- `bg-primary`, `bg-secondary`, `bg-accent` for layout
- `bg-info`, `bg-success`, `bg-warning`, `bg-error` for large areas
- Any Tailwind color like `bg-blue-500`, `bg-gray-100`
- Same background for canvas AND surfaces (creates flatland)

### Text Colors

| Use Case | Class | When to Use |
|----------|-------|-------------|
| Primary text | `text-base-content` | Default, headings |
| Secondary text | `text-base-content/60` | Descriptions, metadata |
| Muted text | `text-base-content/40` | Timestamps, hints |
| Link text | `link` or `text-primary` | Interactive text |
| Error text | `text-error` | Validation messages |

### Border Colors

| Use Case | Class | When to Use |
|----------|-------|-------------|
| Default border | `border-base-300` | Cards, inputs |
| Focus border | `border-primary` | One active element |
| Divider | `divider` | Section separation |
| Error state | `border-error` | Invalid inputs |

### Button Colors

| Use Case | Class | When to Use |
|----------|-------|-------------|
| Primary CTA | `btn-primary` | ONE per viewport |
| Secondary action | `btn-outline` | Important but not main |
| Subtle action | `btn-ghost` | Tertiary, cancel |
| Danger action | `btn-error` | Delete, destructive |
| Disabled | `btn-disabled` | Unavailable action |

---

## 3. Layout Rules

### The 12-Column Grid

Every page content area uses:
```html
<div class="grid grid-cols-1 md:grid-cols-12 gap-6">
  <!-- Content with col-span-X -->
</div>
```

### Standard Spans

| Content | Desktop | Mobile |
|---------|---------|--------|
| Full width | `md:col-span-12` | `col-span-1` |
| Main content | `md:col-span-8` | `col-span-1` |
| Sidebar | `md:col-span-4` | `col-span-1` |
| Equal columns | `md:col-span-4` | `col-span-1` |
| Centered | `md:col-span-6 md:col-start-4` | `col-span-1` |

### Spacing Scale

| Use | Class | Pixels |
|-----|-------|--------|
| Related items | `gap-2` | 8px |
| Section items | `gap-4` | 16px |
| Major sections | `gap-6` | 24px |
| Page sections | `gap-8` | 32px |
| Margin bottom | `mb-6` | 24px |

### Card Structure

Every card follows:
```html
<div class="card bg-base-100 shadow">
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <!-- Content -->
    <div class="card-actions justify-end">
      <!-- Buttons -->
    </div>
  </div>
</div>
```

Compact variant for lists:
```html
<div class="card card-compact bg-base-100 shadow">
  ...
</div>
```

---

## 4. Mobile Requirements

### Touch Targets
- Minimum button size: `btn` (44px height)
- Never use `btn-xs` for primary actions
- Links in lists need padding: `py-3`

### Responsive Patterns
- Grid: `grid-cols-1 md:grid-cols-12`
- Stats: `stats-vertical md:stats-horizontal`
- Steps: `steps-vertical md:steps-horizontal` (if >4 steps)
- Navigation: Drawer on mobile, navbar on desktop

### Testing Viewport
- Primary: 375px (iPhone SE)
- All touch targets visible without zoom
- No horizontal scroll

---

## 5. Anti-Patterns (NEVER DO)

### Visual Crimes
- Large colored background panels
- Multiple `btn-primary` buttons in one view
- Nested cards (card inside card)
- Custom CSS for basic components
- `alert` for non-urgent information

### Layout Crimes
- Hardcoded pixel widths
- Missing responsive breakpoints
- Content outside grid wrapper
- Inconsistent card patterns on same page

### Code Crimes
- Inline styles for anything
- Tailwind colors (bg-blue-500) instead of semantic
- Custom div where daisyUI component exists
- Missing form-control wrapper

---

## 6. Component Checklist

When building a new page, verify:

**Elevation (FIRST - from Section 0):**
- [ ] Page sits on `bg-base-200` canvas (via base.html)
- [ ] All cards/surfaces have `bg-base-100 shadow-md`
- [ ] Clear visual contrast between canvas and surfaces
- [ ] No harsh background differences INSIDE surfaces
- [ ] Inputs use borders for definition, not background colors

**Structure:**
- [ ] Extends base.html
- [ ] Has page header (h1 + description)
- [ ] Uses 12-column grid wrapper
- [ ] Cards follow standard pattern

**Colors:**
- [ ] No large colored backgrounds
- [ ] Text uses base-content variants
- [ ] Borders use base-300
- [ ] Only one btn-primary visible

**Mobile:**
- [ ] Touch targets 44px+
- [ ] Grid responsive (grid-cols-1 md:grid-cols-12)
- [ ] No horizontal scroll at 375px

**Components:**
- [ ] Status shown with badge/indicator (not alert)
- [ ] Expandable content uses collapse
- [ ] Forms use form-control pattern
- [ ] Actions placed consistently

---

## Quick Reference: Component Classes

```
BUTTONS:    btn btn-primary | btn-outline | btn-ghost | btn-error
CARDS:      card bg-base-100 shadow
INPUTS:     input input-bordered | select select-bordered
BADGES:     badge badge-success | badge-warning | badge-error
ALERTS:     alert alert-info | alert-warning (RARE, small)
STATS:      stats (container) + stat (item)
STEPS:      steps + step + step-primary
TABLE:      table table-zebra table-pin-rows
COLLAPSE:   collapse collapse-arrow (default closed)
JOIN:       join + join-item (grouped buttons)
INDICATOR:  indicator + indicator-item badge
PROGRESS:   progress progress-primary
TOAST:      toast (positioned, ephemeral)
```
