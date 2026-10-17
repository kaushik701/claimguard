# Day 8: Evaluation, ablations, portfolio, reports

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `eval/run.py` for the holdout and dev sets with metrics in docs/EVAL_PLAN.md; `--ablate` options; writes
   reports + `eval_runs`. `eval kappa` for the two labellers.
2. **Real-model holdout run** with Groq/Gemini (Kaushik's keys); commit the report.
3. `/eval/runs`, `/portfolio` (heatmap, by regulator/surface, phrasing clusters via embeddings + agglomerative
   clustering, trend), `/reports/{audit_id}.html`.
## Antigravity
Eval page (metric tiles vs targets, run history, confusion by type, ablation bars, reliability diagram),
Portfolio page, Settings page (provider status from /health).
## Done when
Eval page shows a real holdout run with honest numbers; README results table filled from it.
