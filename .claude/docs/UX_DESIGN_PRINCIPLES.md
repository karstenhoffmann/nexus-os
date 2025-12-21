# Nexus OS: UX Design Principles

> This document governs HOW to think about page design, not just WHAT components to use.
> Read this BEFORE any redesign. Reference DAISY_INTENT_SPECS.md for component mapping.

## The Designer Mindset

When redesigning any page, you are a senior UX designer at a company like Apple, Uber, or Stripe.
You care about:
- **User goals** over feature completeness
- **Information hierarchy** over visual balance
- **User flow** over structural templates
- **Delight** over compliance

## Phase 0: UX Analysis (MANDATORY before any code)

### Step 1: Page Purpose Statement
Write ONE sentence answering: "What does this page help the user DO?"

**Examples:**
- Sync page: "Start a sync and monitor its progress"
- Compare page: "Compare embedding models to choose the best one"
- Queries page: "Create and run saved searches"

### Step 2: User Flow Mapping
Draw the user's journey:

```
[Entry] → [Primary Action] → [Feedback/Results] → [Decision/Exit]
```

**Example (Compare page):**
```
[Land on page] → [Enter search query] → [See comparison results] → [Decide which model is better]
```

### Step 3: Information Hierarchy
Rank all page elements by importance (user perspective, not technical):

| Priority | Element | Why |
|----------|---------|-----|
| 1 | Search form | It's the primary action |
| 2 | Quick stats (winner) | User's main question answered |
| 3 | Detailed results | Supporting evidence |
| 4 | Provider status | Secondary context |
| 5 | Hints | Only for new users |

### Step 4: State Inventory
Every interactive page needs these states designed:

- [ ] **Empty state**: Before first action (guiding, not blank)
- [ ] **Loading state**: During async operations (skeleton + feedback)
- [ ] **Success state**: Results, confirmation, next steps
- [ ] **Error state**: Clear message + recovery path

---

## Visual Hierarchy Principles

### The 3-Second Rule
User should understand the page's purpose within 3 seconds of landing.

**Test:** Cover everything except the top 400px. Is the page purpose clear?

### Weight = Importance
Visual weight (size, color, shadow, position) must match information importance.

| Weight Signal | Use For |
|---------------|---------|
| Largest text | Page title or primary metric |
| Primary color | Interactive triggers only |
| Shadow/elevation | Actionable cards |
| Top position | Primary action or insight |
| Collapsed/bottom | Secondary/reference info |

### Progressive Disclosure
Don't show everything at once. Layer information:

1. **Glanceable**: Stats, status badges, key metrics
2. **Scannable**: Headers, summaries, preview text
3. **Readable**: Full content, details, explanations
4. **Discoverable**: Help, hints, advanced options (collapsed)

---

## Page Layout Patterns

### Pattern: Action-First Page
**Use for:** Tools, utilities, forms (Compare, Sync, Create)

```
┌─────────────────────────────────────┐
│  Hero Section: Title + Action       │  ← Primary action visible immediately
├─────────────────────────────────────┤
│  Status/Context (compact)           │  ← Supporting info, minimal
├─────────────────────────────────────┤
│  Results Area (appears after action)│  ← Dynamic, prominent when visible
├─────────────────────────────────────┤
│  Help/Hints (collapsed)             │  ← De-prioritized
└─────────────────────────────────────┘
```

### Pattern: Browse-First Page
**Use for:** Lists, libraries, collections (Queries, Documents)

```
┌─────────────────────────────────────┐
│  Header: Title + Create Action      │  ← "Add new" at top
├─────────────────────────────────────┤
│  Filters/Search (optional)          │  ← Compact, inline
├─────────────────────────────────────┤
│  List of Items                      │  ← Main content
│  (with inline actions)              │
├─────────────────────────────────────┤
│  Pagination/Load More               │  ← If needed
└─────────────────────────────────────┘
```

### Pattern: Dashboard Page
**Use for:** Overview, status, monitoring (Home, Admin)

```
┌─────────────────────────────────────┐
│  Stats Row (key metrics)            │  ← Glanceable KPIs
├───────────────────┬─────────────────┤
│  Primary Content  │  Sidebar/Actions│  ← 8/4 or 9/3 split
│  (main focus)     │  (quick access) │
└───────────────────┴─────────────────┘
```

---

## State Design Patterns

### Empty State
Never show a blank area. Guide the user:

```html
<div class="text-center py-12">
  <div class="text-5xl mb-4 opacity-20">🎯</div>
  <p class="text-base-content/50">Guiding text explaining what to do</p>
</div>
```

### Loading State
Show skeleton + spinner, positioned where results will appear:

```html
<div class="flex items-center justify-center gap-3 py-8">
  <span class="loading loading-spinner loading-lg text-primary"></span>
  <span class="text-base-content/60">Loading message...</span>
</div>
<!-- Skeleton cards below -->
<div class="card animate-pulse">...</div>
```

### Error State
Clear message + recovery option:

```html
<div class="alert alert-error">
  <span>Error description</span>
  <button class="btn btn-sm">Retry</button>
</div>
```

### Success/Results State
Animate entry, highlight key insights:

```html
<section x-show="results.length > 0"
         x-transition:enter="transition ease-out duration-300"
         x-transition:enter-start="opacity-0 translate-y-4"
         x-transition:enter-end="opacity-100 translate-y-0">
  <!-- Results content -->
</section>
```

---

## Interaction Design

### Hover States
Every clickable element needs hover feedback:

```html
<!-- Cards -->
<div class="card hover:shadow-lg transition-shadow">

<!-- List items -->
<a class="hover:bg-base-200/50 transition-colors">

<!-- Text links -->
<a class="link link-primary hover:link-hover">
```

### Loading in Buttons
Show spinner, disable interaction:

```html
<button :disabled="loading">
  <span x-show="!loading">Action</span>
  <span x-show="loading" class="loading loading-spinner loading-sm"></span>
</button>
```

### Transitions
Smooth state changes:

```html
x-transition:enter="transition ease-out duration-200"
x-transition:leave="transition ease-in duration-150"
```

---

## Information Density Rules

### Consolidate Related Info
❌ Bad: 3 cards for 3 data points each
✅ Good: 1 stats bar with 3 stats

### Use Progressive Disclosure
❌ Bad: Help text always visible
✅ Good: `collapse collapse-arrow` (default closed)

### Compact Status Indicators
❌ Bad: Full cards for status info
✅ Good: Inline pills/badges

```html
<!-- Compact status pills -->
<div class="flex gap-4">
  <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-base-200/70 text-sm">
    <span class="w-2 h-2 rounded-full bg-success"></span>
    <span class="font-medium">OpenAI</span>
    <span class="text-base-content/50">402ms</span>
  </div>
</div>
```

---

## Quick Stats Bar Pattern

For pages that compare or show metrics, use a stats bar for immediate insights:

```html
<div class="stats stats-horizontal bg-base-100 shadow w-full">
  <div class="stat py-3 px-4">
    <div class="stat-title text-xs">Winner Label</div>
    <div class="stat-value text-lg text-success">Value</div>
    <div class="stat-desc">Context</div>
  </div>
  <!-- 2-4 stats -->
</div>
```

---

## Anti-Patterns (UX Level)

| Anti-Pattern | Why It's Bad | Fix |
|--------------|--------------|-----|
| Action buried below fold | User can't find primary task | Hero section with action |
| Results far from trigger | Disconnect between action and feedback | Results appear near action |
| Status cards dominating | Secondary info stealing focus | Compact pills/badges |
| Help always expanded | Clutters for repeat users | Collapse, default closed |
| No empty state | Blank page is confusing | Guiding empty state |
| No loading feedback | User unsure if action worked | Spinner + skeleton |
| Same visual weight everywhere | Nothing stands out | Vary size, shadow, position |

---

## Redesign Checklist

Before finalizing any redesign, verify:

### UX Analysis
- [ ] Page purpose statement written
- [ ] User flow mapped
- [ ] Information hierarchy ranked
- [ ] All states designed (empty, loading, success, error)

### Visual Hierarchy
- [ ] Primary action visible without scroll
- [ ] Key insight/metric prominent
- [ ] Secondary info de-prioritized (compact or collapsed)
- [ ] Visual weight matches importance

### Interaction
- [ ] Hover states on all interactive elements
- [ ] Loading feedback in buttons
- [ ] Smooth transitions for state changes
- [ ] Error states with recovery paths

### Iteration
- [ ] Screenshot before
- [ ] Screenshot after
- [ ] Compared critically (not just compliance)
- [ ] Iterated until hierarchy is clear
