---
name: design-audit
description: Advanced UI gatekeeper. UX-first analysis, then component compliance, with Playwright visual verification.
---
# Design Audit Protocol (Nexus v2025)

## CRITICAL: UX-First Approach

**Before ANY code changes, complete Phase 0.**
Reference: `UX_DESIGN_PRINCIPLES.md` for full guidance.

---

## Phase 0: UX Analysis (MANDATORY)

### Step 1: Capture Current State
```
browser_navigate → http://localhost:8000/{page}
browser_take_screenshot → {page}-before.png
```

### Step 2: Page Purpose Statement
Answer in ONE sentence: "What does this page help the user DO?"

### Step 3: User Flow
Map the journey: `[Entry] → [Action] → [Feedback] → [Decision]`

### Step 4: Information Hierarchy
Rank ALL page elements by user importance (1 = most important):

| Priority | Element | Current Treatment | Should Be |
|----------|---------|-------------------|-----------|
| 1 | ? | ? | ? |
| 2 | ? | ? | ? |
| ... | ... | ... | ... |

### Step 5: State Inventory
Check which states exist:
- [ ] Empty state (before first action)
- [ ] Loading state (during async)
- [ ] Success state (results)
- [ ] Error state (with recovery)

### Step 6: UX Verdict
Before proceeding, answer:
- Does visual weight match information importance? (Y/N)
- Is primary action visible without scrolling? (Y/N)
- Are secondary elements de-prioritized? (Y/N)
- Are all states designed? (Y/N)

**If any answer is NO → redesign needed (not just component swap)**

---

## Phase 1: Component Inspection

Only after Phase 0 is complete.

1. **Component Match:** Custom `<div>` where DaisyUI exists?
   - Check: `collapse`, `stats`, `badge`, `steps`, `join`, `indicator`
   - Reference: DAISY_INTENT_SPECS.md

2. **Color Compliance:** Large colored backgrounds?
   - Rule: 90% neutral (base-100/200), color only for interactive/status
   - Fix: `badge`, `alert` (small), or `collapse`

3. **Responsive Grid:** Uses `grid grid-cols-1 md:grid-cols-12 gap-6`?
   - Reference: PAGE_TEMPLATES.md

4. **Touch Targets:** At least 44px?
   - Buttons: `btn-md` minimum
   - List links: `py-3` padding

---

## Phase 2: Implementation

### If UX Redesign Needed:
1. Apply UX_DESIGN_PRINCIPLES.md patterns
2. Design ALL states (empty, loading, success, error)
3. Ensure visual hierarchy matches importance
4. Add hover states and transitions

### If Only Component Fixes:
1. Swap custom elements for DaisyUI
2. Maintain existing hierarchy
3. Preserve functionality

---

## Phase 3: Visual Verification

### Desktop Check (1200x800)
```
browser_resize → 1200x800
browser_take_screenshot → {page}-desktop.png
```

Verify:
- [ ] Primary action visible without scroll
- [ ] Visual hierarchy clear (weight = importance)
- [ ] One `btn-primary` per viewport
- [ ] No large colored panels
- [ ] All states have designs

### Mobile Check (375x667)
```
browser_resize → 375x667
browser_take_screenshot → {page}-mobile.png
```

Verify:
- [ ] No horizontal scroll
- [ ] Touch targets 44px+
- [ ] Content readable
- [ ] Actions accessible

---

## Phase 4: Iteration Loop

**Do NOT present for approval until confident this is the best possible design.**

Ask yourself:
1. Would a senior designer at Apple/Stripe approve this?
2. Is the user's goal achievable in minimum steps?
3. Does visual hierarchy guide the eye correctly?
4. Are there any anti-patterns from UX_DESIGN_PRINCIPLES.md?

If any doubt → iterate before presenting.

---

## Phase 5: Present for Approval

Open two browser tabs:
- Tab 1: Original (before)
- Tab 2: Redesigned (after)

Report:
1. **Page Purpose:** One sentence
2. **UX Changes:** What hierarchy/flow changed and why
3. **Component Changes:** DaisyUI swaps made
4. **States Added:** Empty/loading/error states
5. **Trade-offs:** What's lost vs gained

Wait for: `approve` | `feedback [details]` | `revert`

---

## Quick Reference

### UX Anti-Patterns
| Issue | Fix |
|-------|-----|
| Action below fold | Hero section |
| Results far from action | Appear in place |
| Status info dominates | Compact pills |
| Help always expanded | Collapse, closed default |
| No empty state | Guiding placeholder |
| No loading feedback | Spinner + skeleton |

### Component Swaps
| Issue | Fix |
|-------|-----|
| Custom badge | `badge badge-neutral` |
| Custom collapse | `collapse collapse-arrow` |
| Custom stats | `stats` + `stat` |
| Custom steps | `steps` + `step` |
| Button text wrap | `whitespace-nowrap inline-flex` |

### State Patterns
| State | Pattern |
|-------|---------|
| Empty | Emoji + guiding text, centered |
| Loading | `loading loading-spinner` + skeleton cards |
| Error | `alert alert-error` + retry button |
| Success | `x-transition` animation on appear |
