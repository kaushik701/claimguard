---
description: Plan and build the next unfinished day from docs/BUILD_PLAN.md
---
1. Read docs/PROGRESS.md and find the first day whose backend column is not "done".
2. Read docs/days/DAY-<N>.md and the docs it references.
3. Enter plan mode. Write a numbered checklist for the Claude Code part only (files to create/change, tests,
   commands, what you need from Kaushik). Flag anything that conflicts with AGENTS.md or docs/reviews/.
4. STOP and wait for Kaushik's OK.
5. Build on branch `cc/day-<N>-<topic>`. Run `cd backend && pytest -q` after each logical step.
6. Run the day's "Done when" checks. Save evidence (report tables, screenshots) under docs/.
7. Update docs/PROGRESS.md (status, what shipped, metric changes and why, open questions). Commit.
$ARGUMENTS
