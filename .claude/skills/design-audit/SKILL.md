---
name: design-audit
description: Advanced UI gatekeeper. Audits code for daisyUI intent mapping and visual hierarchy with Playwright visual verification.
---
# Design Audit Protocol (Nexus v2025)

## Phase 1: Code Inspection

1. **Component Match:** Does this use a custom `<div>` where a daisyUI component exists?
   - Check against: `indicator`, `join`, `swap`, `collapse`, `stats`, `steps`, `badge`
   - Reference: DAISY_INTENT_SPECS.md

2. **Scrap Check:** Is there a large colored box (`bg-primary`, `bg-info`, etc.)?
   - Refactor to: `badge`, `alert` (small), or `collapse`
   - Rule: 90% neutral (base-100/200), color only for interactive/status

3. **Responsive Grid:** Does layout use `grid grid-cols-1 md:grid-cols-12 gap-6`?
   - Reference: PAGE_TEMPLATES.md for skeleton

4. **Mobile Polish:** Are touch targets at least 44px?
   - Buttons: `btn-md` minimum (never `btn-xs` for primary actions)
   - Links in lists: `py-3` padding

## Phase 2: Visual Verification (Playwright)

**When to run:** After any template change, before marking task complete.

### Steps:

1. **Navigate to the changed page:**
   ```
   mcp__playwright__browser_navigate → http://localhost:8000/{page_path}
   ```

2. **Desktop check (1200px):**
   ```
   mcp__playwright__browser_resize → width: 1200, height: 800
   mcp__playwright__browser_snapshot → (inspect accessibility tree)
   ```

   Verify:
   - [ ] No large colored background panels
   - [ ] Cards follow consistent shadow/spacing
   - [ ] One `btn-primary` visible per viewport section
   - [ ] Text hierarchy clear (h1 > h2 > body)

3. **Mobile check (375px):**
   ```
   mcp__playwright__browser_resize → width: 375, height: 667
   mcp__playwright__browser_snapshot → (inspect accessibility tree)
   ```

   Verify:
   - [ ] No horizontal scroll
   - [ ] Touch targets visible and tappable (44px+)
   - [ ] Grid collapses to single column
   - [ ] Navigation accessible via mobile menu

4. **Screenshot evidence (optional, for review):**
   ```
   mcp__playwright__browser_take_screenshot → filename: "audit-{page}-desktop.png"
   mcp__playwright__browser_take_screenshot → filename: "audit-{page}-mobile.png"
   ```

## Output Requirement

Before showing code, report:

1. **Code Crimes Found:** List 2+ specific issues and fixes using DAISY_INTENT_SPECS.md
2. **Visual Verdict:** PASS/FAIL for desktop and mobile with brief notes

Example output:
```
## Design Audit Results

### Code Crimes Fixed:
1. Replaced custom status `<div class="bg-green-500 p-4">` → `badge badge-success`
2. Added `grid-cols-1 md:grid-cols-12` wrapper (was missing responsive)

### Visual Verification:
- Desktop (1200px): PASS - consistent card shadows, single primary CTA
- Mobile (375px): PASS - no horizontal scroll, touch targets adequate
```

## Quick Reference

| Issue | Fix |
|-------|-----|
| Large colored box | `badge` or `collapse collapse-arrow` |
| Custom button styles | `btn btn-primary/outline/ghost` |
| Missing grid wrapper | `grid grid-cols-1 md:grid-cols-12 gap-6` |
| Tiny touch targets | `btn-md` minimum, `py-3` for list links |
| Multiple primary buttons | Keep one, demote others to `btn-outline` |
| Nested cards | Flatten hierarchy, use `divider` instead |
