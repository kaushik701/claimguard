# Day 2: Clauses, tags, definitions, API skeleton, contract freeze

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `kb/segment.py`: clause splitting by each document's numbering (docs/KNOWLEDGE_BASE.md §Clauses). ASCI: use
   the TOC page (book p.3) to get guideline section start pages; inside sections split on numbered headings and
   (a)(b) items; join short list items to their parent. FSSAI: Regulation N, sub-regulation (N), clause (a),
   Schedules. CCPA-GW: OCR paragraphs with numbers; unreadable numbers → `CCPA-GW-p{page}-{slug}`.
   Clause IDs are stable (doc prefix + number + page if numbers repeat).
2. Dedupe identical text across documents (keep both IDs, mark `duplicate_of`).
3. `kb/tagger.py`: P1 prompt over every clause (batch 10 per call), keyword cross-check, write tags; apply
   `knowledge/overrides/tags.yaml` and `scope.yaml` last.
4. `kb/xref.py`: definitions ("X means …") and cross-reference edges.
5. `knowledge/checks/spot_checks.yaml`: 20 sentences copied by hand from the PDFs (Kaushik provides 10, Claude
   Code proposes 10 and shows the page for each); `kb check` must find all verbatim.
6. FastAPI skeleton with all routes from docs/API_CONTRACT.md returning fixture data; export
   `frontend/src/api/openapi.json`. **Stop and ask Kaushik to approve the contract.** After approval it is frozen.
7. `/kb/documents`, `/kb/clauses`, `/kb/clauses/{id}`, `/kb/pages/...` implemented for real.
## Antigravity
FlagCard, CitationBlock (serif quote, doc · section · clause · page, OCR badge), PageViewer drawer (page image
with highlighted quote box), RewriteDiff, ConfidenceBar. Use mocks.
## Tests
test_segment_asci (clause 1.1, 1.2 present with right pages), test_segment_fssai (Regulation 4 sub-parts),
test_no_clause_from_legacy_pages, test_spot_checks, test_tag_overrides_survive_rebuild, test_contract_routes.
## Done when
Spot checks 20/20; clauses per doc in report; openapi.json approved and committed.
