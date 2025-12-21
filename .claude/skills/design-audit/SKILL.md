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

## Phase 2: Visual Comparison (MANDATORY)

**Two-tab browser comparison for every UI change.**

### Steps:

1. **Open Before Tab:**
   ```
   browser_navigate → http://localhost:8000/{page} (Tab 1 = current state)
   browser_take_screenshot → {page}-before.png
   ```

2. **Implement Changes** (preview state, not finalized)

3. **Open After Tab:**
   ```
   browser_tabs → action: "new"
   browser_navigate → http://localhost:8000/{page} (Tab 2 = new state)
   browser_take_screenshot → {page}-after.png
   ```

4. **Verify (both viewports):**
   ```
   browser_resize → 1200x800 (desktop) then 375x667 (mobile)
   ```
   - [ ] No large colored background panels
   - [ ] Cards follow consistent shadow/spacing
   - [ ] One `btn-primary` per viewport
   - [ ] Mobile: no horizontal scroll, 44px+ touch targets
   - [ ] **TEXT INTEGRITY:** All button/badge text fully readable (no line breaks, no truncation)
   - [ ] **ICON ALIGNMENT:** Icons and text in buttons on same line, properly spaced

5. **Present for Approval:**
   - "Browser has 2 tabs: Tab 1 = Before (don't refresh), Tab 2 = After"
   - List changes made and trade-offs
   - Wait for: `approve` | `adjust [feedback]` | `revert`

6. **Handle Response:**
   - `approve` → finalize, update MISSION_CONTROL
   - `adjust` → revert changes, apply feedback, repeat from step 2
   - `revert` → restore original file, end task

## Output Requirement

Report before requesting approval:

1. **Code Crimes Found:** 2+ issues with fixes (reference DAISY_SPECS.md)
2. **Trade-offs:** What's lost vs gained
3. **Visual Verdict:** PASS/FAIL for desktop and mobile

## Quick Reference

| Issue | Fix |
|-------|-----|
| Large colored box | `badge` or `collapse collapse-arrow` |
| Custom button styles | `btn btn-primary/outline/ghost` |
| Missing grid wrapper | `grid grid-cols-1 md:grid-cols-12 gap-6` |
| Tiny touch targets | `btn-md` minimum, `py-3` for list links |
| Multiple primary buttons | Keep one, demote others to `btn-outline` |
| Nested cards | Flatten hierarchy, use `divider` instead |
| **Button text wrapping** | Add `whitespace-nowrap`, use `inline-flex items-center gap-1` for icon+text |
| **Icon misalignment** | Wrap icon+text in `<span class="inline-flex items-center gap-1">` |
