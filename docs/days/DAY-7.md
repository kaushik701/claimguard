# Day 7: Review loop and learning

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `PATCH /flags/{id}` and `GET /flags` (queue with filters). Reason codes: wrong_clause, not_a_claim,
   substantiated, puffery, wrong_risk, other.
2. `learning/memory.py`: embed accepted/edited decisions (claim + clause + final risk + reason) and dismissals
   (hard negatives); retrieve top-3 similar for P3/P6 prompts. Exclude anything whose text matches holdout.
3. `learning/stats.py`: per-clause and per-claim-type accept/dismiss rates; reranker re-weighting (min 10 obs).
4. `agents/calibrate.py`: Beta prior → isotonic regression once ≥ 100 labels; reliability bins stored.
5. `learning/report.py`: weekly report via P11 (manual command).
## Antigravity
Review queue: table with filters, sort by confidence, bulk actions, keyboard; reason-code picker on dismiss.
## Tests
test_feedback_changes_memory (a dismissed example appears in the next prompt for a similar claim),
test_holdout_never_in_memory, test_calibration_monotonic.
## Done when
Dismissing a flag with "puffery" makes a near-identical claim come back LOW or with lower confidence (fake LLM
fixture demonstrates the prompt change; real-key demo recorded).
