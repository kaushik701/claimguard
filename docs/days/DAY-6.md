# Day 6: Ask the Guidelines (copilot)

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `agents/copilot.py`: question rewrite (P10) → hybrid retrieval without claim-type filter → rerank → answer (P9)
   → citation check (each quote verbatim) → refusal when top score below threshold or `covered=false`.
2. Sessions stored in `chat_sessions` (last 4 turns).
3. `data/gold/copilot_gold.jsonl` (40 questions, 10 out of scope) + `python -m claimguard.eval copilot`.
## Antigravity
Ask screen: chat, starter questions, numbered citations with "Open page", refusal styling.
## Tests
test_copilot_refuses_out_of_scope, test_copilot_citations_verbatim.
## Done when
Grounded answer rate ≥ 0.9 and correct refusals ≥ 0.9 on copilot gold.
