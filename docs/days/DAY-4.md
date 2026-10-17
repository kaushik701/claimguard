# Day 4: Agent chain end to end

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `agents/normalise.py` (text/html; pdf upload via text layer), `extract.py` (P3), `rule_extract.py` (regex
   taxonomy, port the 10 claim-type patterns + qualifier/footnote detection), `merge.py` (span overlap ≥ 50%).
2. `judge.py` (P6, one call per input, includes definitions + memory examples placeholder), `verify.py`
   (code citation guard: span in input, clause retrieved, quote verbatim ≥ 20 chars), `verifier.py` (P7 on a
   different model, can only lower risk), `rewrite.py` (P8), `pipeline.py` orchestrating with per-step logging
   to `runs`, deterministic fallback to rule judge when the LLM fails (banner flag in result).
3. `POST /audits` + SSE `/audits/{id}/events` + `GET /audits/{id}` real.
4. `data/samples/`: the fictional listings provided; `data/gold/listings_golden/` 12 inputs with recorded LLM
   outputs (record once with a real key, commit fixtures).
## Antigravity
Wire Audit to the real API (`VITE_USE_MOCKS=false`), live SSE progress, claim highlighting, keyboard j/k/a/d/e.
## Tests
test_merge, test_verify_drops_paraphrase, test_verify_drops_unretrieved_clause, test_verifier_only_lowers,
test_pipeline_fallback_on_llm_error, test_injection_text_is_data, golden listings regression.
## Done when
All 12 golden listings produce expected flags with the fake LLM; one real-key run screenshot in PROGRESS.md.
