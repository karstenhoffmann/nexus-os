# Nexus OS - Project Constitution

## 1. Governance (Rules of the House)

- **Librarian Protocol:** Never append. MERGE info into existing docs.
- **Teacher Protocol:** If the user is a beginner, explain "Why" before "How."
- **Clean Room:** Run `/janitor` after every major task completion.
- - **Reality Check:** Before making recommendations based on "current" dates or versions, run \`date\` to synchronize with the actual present.

## 2. Directory Mapping (The Source of Truth)

- Product Vision & Phases: @.claude/docs/product_brief.md
- Technical Specs & Rules: @.claude/docs/architecture.md
- Work-in-Progress Ideas: @.claude/docs/whiteboard.md
- Active Task & Progress: @.claude/records/MISSION_CONTROL.md
- Decision History: @.claude/records/DECISION_LOG.md

## 3. Tech Stack Constraints

- Python 3.14 + FastAPI + HTMX + Alpine.js + daisyUI.
- NO Node.js. Use SQLite-vec for semantic search.

## 4. Standard Workflows

- **On "Vague Idea":** Stop coding. Research in `whiteboard.md` first.
- **On "Pause/Stopping":** Invoke the `checkpoint` skill immediately.
- **On "Resume":** Read the `PAUSED SESSION` block in MISSION_CONTROL.md and ask for verification before starting.
- **On Version Planning:** Always cross-reference the system date with the planned roadmap in product_brief.md to ensure we aren't living in the past.
- - **On Milestone Completion:** Proactively run the `librarian` skill. Propose the Git commit, then advise the user to `/clear` and resume with "let's continue".

# Nexus OS Project Intelligence

## Design Governance (IMPERATIVE)

1. **The Circuit:** Before any UI task, invoke `design-audit`.
2. **Visual Approval Gate:** UI changes require two-tab Playwright comparison (before/after) with explicit user approval before finalization.
3. **Context Anchoring:** Read `llms.txt` to understand component hierarchy.
4. **Sparse Color:** Do not use primary/secondary colors for layout panels. Use them only for interactive triggers.
5. **Fuzzy Search:** If a component name is unknown, search `DAISY_SPECS.md` for the "Intent" (e.g., "how to show status").

## Skills

- **Librarian:** Milestone and Git management.
- **Checkpoint:** Session save logic.
- **Design-Audit:** UI fidelity and "Anti-Scrap" gatekeeper.
