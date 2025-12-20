---
name: checkpoint
description: The "Save Game" tool. Use this when pausing work mid-task to prevent context loss.
---
# Checkpoint Protocol (v2.2)

## Procedure
1. **Secure State:** Run `git add .` immediately to stage current progress.
2. **Context Capture:** Update MISSION_CONTROL.md with a `## ⏸️ PAUSED SESSION` block.
3. **Mental Thread:** Identify the exact file, line number, and the "next logical thought" (the intent that isn't in the code yet).
4. **Instruction:** Remind the user to `/clear` and explain that the state is safe in Git.
