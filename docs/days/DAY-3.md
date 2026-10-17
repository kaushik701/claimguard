# Day 3: Hybrid retrieval and reranking

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `retrieval/bm25.py`, `dense.py` (fastembed bge-small, LanceDB), `fusion.py` (RRF k=60), `filters.py`
   (claim type incl. general_truthfulness, category, surface, regulator scope), query expansion (P4, cached),
   graph expansion (1 hop), `rerank.py` (P5, top 15 → 5, score threshold → "not covered").
2. `data/gold/retrieval_gold.jsonl`: 100 claims with expected clause_ids (Claude Code drafts from dev.jsonl,
   Kaushik reviews 30 of them).
3. `python -m claimguard.eval retrieval` → recall@1/5/10 for BM25, dense, hybrid, hybrid+rerank.
4. Kaushik labels the first 50 holdout items blind (see docs/reviews/01_OFFICE_HOURS.md assignment).
## Antigravity
Knowledge explorer: document list with build stats; clause browser (search, filters); clause detail with
PageViewer side by side; tag editor calling PATCH (mock until wired).
## Tests
test_fusion_order, test_filters_scope (FSSAI never returned for home-care), test_rerank_not_covered.
## Done when
Hybrid+rerank recall@5 ≥ 0.85 on retrieval gold, table in PROGRESS.md.
