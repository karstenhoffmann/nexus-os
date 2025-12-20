# Skill: Librarian & Janitor (v2.1 - Git Support)
**Goal:** Maintain documentation and propose Git commits at milestones.

**Procedure:**
1. **Merge & Prune:** Move completed tasks in MISSION_CONTROL.md to "Recent Completions."
2. **Commit Proposal:** Whenever a logical sub-task is finished:
   - Analyze the changes.
   - Propose a `git commit -m "..."` command using Conventional Commits (feat, fix, docs, chore).
3. **Cleanup:** Run `/janitor` to remove cache/temp files.
4. **Compression:** Ensure no .md file exceeds 2,000 words.
