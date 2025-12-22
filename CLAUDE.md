# Nexus OS - Project Constitution

## 1. Governance (Rules of the House)

- **Librarian Protocol:** Never append. MERGE info into existing docs.
- **Teacher Protocol:** If the user is a beginner, explain "Why" before "How."
- **Clean Room:** Run `/janitor` after every major task completion.
- **Reality Check:** Before making recommendations based on "current" dates or versions, run \`date\` to synchronize with the actual present.

## 2. Directory Mapping (The Source of Truth)

### Auto-loaded (essential context for every task)
- Active Task & Progress: @.claude/records/MISSION_CONTROL.md
- Technical Specs & Rules: @.claude/docs/architecture.md
- Product Vision & Phases: @.claude/docs/product_brief.md

### Read when relevant
- Work-in-Progress Ideas: `.claude/docs/whiteboard.md` (for Digest 2.0 / feature design)
- DaisyUI Index: `.claude/docs/daisyui_llms.txt` (entry point for UI component docs)
- DaisyUI Full Specs: `.claude/docs/DAISY_SPECS.md` (complete component reference)

## 3. Tech Stack Constraints

- Python 3.14 + FastAPI + HTMX + Alpine.js + daisyUI.
- NO Node.js. Use SQLite-vec for semantic search.

## 4. Standard Workflows

- **On "Vague Idea":** Stop coding. Research in `whiteboard.md` first.
- **On "Pause/Stopping":** Invoke the `checkpoint` skill immediately.
- **On "Resume":** Read the `PAUSED SESSION` block in MISSION_CONTROL.md and ask for verification before starting.
- **On Version Planning:** Always cross-reference the system date with the planned roadmap in product_brief.md to ensure we aren't living in the past.
- **On Milestone Completion:** Proactively run the `librarian` skill. Propose the Git commit, then advise the user to `/clear` and resume with "let's continue".

# Nexus OS Project Intelligence

## Design Governance (IMPERATIVE)

1. **The Circuit:** Before any UI task, invoke `design-audit`.
2. **Visual Approval Gate:** UI changes require two-tab Playwright comparison (before/after) with explicit user approval before finalization.
3. **Context Anchoring:** Read `.claude/docs/daisyui_llms.txt` to understand component hierarchy.
4. **Sparse Color:** Do not use primary/secondary colors for layout panels. Use them only for interactive triggers.
5. **Fuzzy Search:** If a component name is unknown, search `.claude/docs/DAISY_SPECS.md` for the "Intent" (e.g., "how to show status").

## Skills

- **Librarian:** Milestone and Git management.
- **Checkpoint:** Session save logic.
- **Design-Audit:** UI fidelity and "Anti-Scrap" gatekeeper.

## DaisyUI Component Rules (NON-NEGOTIABLE)

### NEVER add these to form elements:
- `bg-transparent` - breaks select dropdowns and input backgrounds
- `border-0` or `border-none` - breaks DaisyUI borders
- `outline-none` or `focus:outline-none` - breaks focus states
- `focus-within:*` custom overrides - DaisyUI handles focus
- `transition-*` on form elements - DaisyUI handles animations

### ALWAYS use standard DaisyUI patterns:
- Inputs: `input input-bordered`
- Selects: `select select-bordered`
- Joined inputs: `join` + `join-item` on each element
- Label wrapper: `<label class="input input-bordered">` with inner `<input class="grow">`

### Form element sizing:
- Primary/hero: `input-lg`, `select-lg`, `btn-lg`
- Regular forms: default (no size modifier)
- Compact/inline: `input-sm`, `select-sm`, `btn-sm`

### Responsive layouts:
- Prefer `flex flex-wrap gap-4` with `min-w-*` for natural wrapping
- Avoid aggressive grid breakpoints that stack too early
