# Nexus OS: Page Template System

> Enforced structural patterns for consistent UI. Each template is a "Block" that Claude Code must follow.

## Template Philosophy

**Why Templates?**
- Consistency through constraint: Every page follows a proven structure
- Faster development: Copy the skeleton, fill in content
- Easier auditing: Deviations are immediately visible

**Core Principles:**
1. Every page starts with the same grid wrapper
2. Every page has a predictable header pattern
3. Content areas use consistent spacing
4. Actions follow placement rules

---

## Base Page Wrapper (MANDATORY)

Every page template MUST be wrapped in this structure:

```html
{% extends "base.html" %}
{% block content %}

<!-- Page Header -->
<div class="mb-6">
  <h1 class="text-2xl font-bold">Page Title</h1>
  <p class="text-base-content/60">Brief description of page purpose</p>
</div>

<!-- Main Content Grid -->
<div class="grid grid-cols-1 md:grid-cols-12 gap-6">
  <!-- Content goes here using col-span-X -->
</div>

{% endblock %}
```

---

## Template 1: Dashboard Page

**Use For:** Home, Admin, Overview pages
**Structure:** Stats row + main content grid

```html
{% extends "base.html" %}
{% block content %}

<div class="mb-6">
  <h1 class="text-2xl font-bold">Dashboard Title</h1>
  <p class="text-base-content/60">Overview description</p>
</div>

<!-- Stats Row (always full width, 2-4 items) -->
<div class="stats stats-vertical md:stats-horizontal shadow w-full mb-6">
  <div class="stat">
    <div class="stat-title">Stat Label</div>
    <div class="stat-value">Value</div>
    <div class="stat-desc">Change or context</div>
  </div>
  <!-- Repeat for 2-4 stats -->
</div>

<!-- Main Content Grid -->
<div class="grid grid-cols-1 md:grid-cols-12 gap-6">
  <!-- Primary Content: col-span-8 or col-span-9 -->
  <div class="md:col-span-8">
    <div class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Section Title</h2>
        <!-- Content -->
      </div>
    </div>
  </div>

  <!-- Sidebar: col-span-4 or col-span-3 -->
  <div class="md:col-span-4">
    <div class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Quick Actions</h2>
        <!-- Actions -->
      </div>
    </div>
  </div>
</div>

{% endblock %}
```

---

## Template 2: List Page

**Use For:** Library, Drafts, Queries, any collection view
**Structure:** Filters + list + pagination

```html
{% extends "base.html" %}
{% block content %}

<div class="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
  <div>
    <h1 class="text-2xl font-bold">Collection Title</h1>
    <p class="text-base-content/60">{{ count }} items</p>
  </div>
  <div class="flex gap-2">
    <!-- Primary action button -->
    <a href="/create" class="btn btn-primary">Add New</a>
  </div>
</div>

<!-- Filters (optional) -->
<div class="card bg-base-100 shadow mb-6">
  <div class="card-body py-4">
    <div class="flex flex-wrap gap-4 items-center">
      <input type="search" placeholder="Search..." class="input input-bordered w-full md:w-64" />
      <select class="select select-bordered">
        <option>All Types</option>
      </select>
      <!-- More filters -->
    </div>
  </div>
</div>

<!-- List Content -->
<div class="grid grid-cols-1 gap-4">
  {% for item in items %}
  <div class="card card-compact bg-base-100 shadow hover:shadow-md transition-shadow">
    <div class="card-body flex-row items-center justify-between">
      <div>
        <h3 class="font-medium">{{ item.title }}</h3>
        <p class="text-sm text-base-content/60">{{ item.subtitle }}</p>
      </div>
      <div class="flex gap-2">
        <a href="/item/{{ item.id }}" class="btn btn-ghost btn-sm">View</a>
      </div>
    </div>
  </div>
  {% endfor %}
</div>

<!-- Pagination -->
<div class="flex justify-center mt-6">
  <div class="join">
    <button class="join-item btn btn-sm">Prev</button>
    <button class="join-item btn btn-sm btn-active">1</button>
    <button class="join-item btn btn-sm">2</button>
    <button class="join-item btn btn-sm">Next</button>
  </div>
</div>

{% endblock %}
```

---

## Template 3: Detail Page

**Use For:** Document detail, Draft detail, Person detail
**Structure:** Header with actions + content sections

```html
{% extends "base.html" %}
{% block content %}

<!-- Header with breadcrumb and actions -->
<div class="mb-6">
  <div class="breadcrumbs text-sm mb-2">
    <ul>
      <li><a href="/collection">Collection</a></li>
      <li>Current Item</li>
    </ul>
  </div>
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold">{{ item.title }}</h1>
      <p class="text-base-content/60">{{ item.metadata }}</p>
    </div>
    <div class="flex gap-2">
      <button class="btn btn-outline">Secondary Action</button>
      <button class="btn btn-primary">Primary Action</button>
    </div>
  </div>
</div>

<!-- Content Grid -->
<div class="grid grid-cols-1 md:grid-cols-12 gap-6">
  <!-- Main Content -->
  <div class="md:col-span-8">
    <div class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Main Content</h2>
        <div class="prose max-w-none">
          {{ content }}
        </div>
      </div>
    </div>
  </div>

  <!-- Metadata Sidebar -->
  <div class="md:col-span-4">
    <div class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title text-base">Details</h2>
        <div class="space-y-3">
          <div>
            <div class="text-sm text-base-content/60">Created</div>
            <div>{{ item.created_at }}</div>
          </div>
          <div>
            <div class="text-sm text-base-content/60">Source</div>
            <a href="{{ item.source_url }}" class="link">Original</a>
          </div>
          <!-- More metadata -->
        </div>
      </div>
    </div>
  </div>
</div>

{% endblock %}
```

---

## Template 4: Form/Settings Page

**Use For:** Admin settings, Prompt editing, Configuration
**Structure:** Sectioned form with clear groupings

```html
{% extends "base.html" %}
{% block content %}

<div class="mb-6">
  <h1 class="text-2xl font-bold">Settings Title</h1>
  <p class="text-base-content/60">Configure options and preferences</p>
</div>

<div class="max-w-3xl">
  <!-- Form Section 1 -->
  <div class="card bg-base-100 shadow mb-6">
    <div class="card-body">
      <h2 class="card-title text-lg">Section Name</h2>
      <p class="text-sm text-base-content/60 mb-4">Section description</p>

      <div class="space-y-4">
        <div class="form-control">
          <label class="label">
            <span class="label-text">Field Label</span>
          </label>
          <input type="text" class="input input-bordered" />
          <label class="label">
            <span class="label-text-alt text-base-content/50">Helper text</span>
          </label>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">Select Field</span>
          </label>
          <select class="select select-bordered">
            <option>Option 1</option>
            <option>Option 2</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <!-- Form Section 2 -->
  <div class="card bg-base-100 shadow mb-6">
    <div class="card-body">
      <h2 class="card-title text-lg">Another Section</h2>
      <!-- More fields -->
    </div>
  </div>

  <!-- Actions (sticky or at bottom) -->
  <div class="flex gap-4 justify-end">
    <button class="btn btn-ghost">Cancel</button>
    <button class="btn btn-primary">Save Changes</button>
  </div>
</div>

{% endblock %}
```

---

## Template 5: Pipeline/Process Page

**Use For:** Sync, Import, Batch operations
**Structure:** Steps indicator + active phase + results

```html
{% extends "base.html" %}
{% block content %}

<div class="mb-6">
  <h1 class="text-2xl font-bold">Process Title</h1>
  <p class="text-base-content/60">Pipeline description</p>
</div>

<!-- Steps Indicator -->
<ul class="steps steps-horizontal w-full mb-8">
  <li class="step step-primary">Step 1</li>
  <li class="step step-primary">Step 2</li>
  <li class="step">Step 3</li>
  <li class="step">Step 4</li>
</ul>

<!-- Active Phase Card -->
<div class="card bg-base-100 shadow mb-6">
  <div class="card-body">
    <div class="flex items-center justify-between mb-4">
      <h2 class="card-title">Current Phase</h2>
      <span class="badge badge-primary">In Progress</span>
    </div>

    <!-- Progress -->
    <progress class="progress progress-primary w-full" value="65" max="100"></progress>
    <div class="flex justify-between text-sm text-base-content/60 mt-1">
      <span>650 of 1000 items</span>
      <span>65%</span>
    </div>

    <!-- Actions -->
    <div class="card-actions justify-end mt-4">
      <button class="btn btn-outline">Pause</button>
      <button class="btn btn-primary">Continue</button>
    </div>
  </div>
</div>

<!-- Results/Log Section (collapsible) -->
<div class="collapse collapse-arrow bg-base-100 shadow">
  <input type="checkbox" />
  <div class="collapse-title font-medium">View Details & Log</div>
  <div class="collapse-content">
    <div class="space-y-2 text-sm font-mono">
      <div class="text-base-content/60">[12:34:56] Processing item 650...</div>
      <!-- Log entries -->
    </div>
  </div>
</div>

{% endblock %}
```

---

## Grid Span Reference

| Content Type | Mobile | Desktop | Notes |
|-------------|--------|---------|-------|
| Full width | col-span-1 | col-span-12 | Stats, hero sections |
| Main content | col-span-1 | col-span-8 | Primary content area |
| Sidebar | col-span-1 | col-span-4 | Metadata, actions |
| Equal thirds | col-span-1 | col-span-4 | Cards in row |
| Equal halves | col-span-1 | col-span-6 | Side-by-side comparison |
| Narrow form | col-span-1 | col-span-6 start-4 | Centered form |

---

## Enforcement Checklist

Before finalizing any template, verify:

- [ ] Uses `grid grid-cols-1 md:grid-cols-12 gap-6` wrapper
- [ ] Page header follows pattern (h1 + description)
- [ ] Cards use `card bg-base-100 shadow`
- [ ] Buttons use semantic variants (primary/ghost/outline)
- [ ] Forms use `form-control` + `label` structure
- [ ] Lists use consistent card pattern
- [ ] No custom background colors (only base-100, base-200)
- [ ] Touch targets are btn-md minimum (h-12)
- [ ] Actions placed at top-right or card-actions
