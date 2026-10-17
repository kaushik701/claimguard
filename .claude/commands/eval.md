---
description: Run the evaluation suite and explain changes
---
1. `cd backend && python -m claimguard.eval run --set holdout` (real keys required; otherwise `--fake`).
2. Also run `eval retrieval` and `eval copilot` if retrieval or copilot code changed.
3. Compare with the previous run in reports/. Make a table of metric deltas vs docs/EVAL_PLAN.md targets.
4. For every metric that moved by more than 0.02, list the items that changed and the likely cause.
5. Never edit holdout files or use holdout items to fix prompts.
$ARGUMENTS
