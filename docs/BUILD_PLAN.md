# Build plan (10 build days)

Two tracks in parallel. **Claude Code** owns `backend/`, `knowledge/`, `data/`, evals. **Antigravity** owns
`frontend/`. The API contract (docs/API_CONTRACT.md) is the only shared surface; it freezes at the end of Day 2.
Until then, Antigravity builds screens against `frontend/src/api/mock/` fixtures.

| Day | Claude Code (backend + AI) | Antigravity (frontend) | Done when |
|---|---|---|---|
| 0 | Repo scaffold, config, LLM client with fake + fallback, CI | Vite app, routing, tokens, layout shell, mock API layer | `pytest` and `npm run build` green |
| 1 | KB ingestion: text, OCR, script detection, page images | Audit screen (paste flow) on mocks | `kb build` covers all 5 PDFs, build report |
| 2 | Segmentation, tagging, definitions, xrefs, spot-checks; FastAPI skeleton; **freeze openapi.json** | Flag card, citation block, page viewer, rewrite diff | 20/20 spot-checks; contract frozen |
| 3 | Hybrid retrieval + reranker + retrieval gold; label 50 holdout items (you) | Knowledge explorer screen | recall@5 reported |
| 4 | Agent chain: extract (LLM + rules + merge), judge, citation guard, verifier, rewriter; SSE | Wire Audit to real API + SSE progress | Golden listings pass |
| 5 | Pack-image path (OCR + vision), HTML/PDF upload; preflight endpoint | Pack-image input with OCR boxes; Pre-flight screen | Image audit end-to-end |
| 6 | Copilot (Ask the Guidelines) + copilot gold | Ask screen | grounded ≥ 0.9 on copilot gold |
| 7 | Review API, feedback, few-shot memory, clause reliability, calibration | Review queue screen + keyboard shortcuts | Feedback changes next audit (test) |
| 8 | Eval runner, ablations, kappa, portfolio API, reports | Eval page, Portfolio page, Settings | Holdout run committed |
| 9 | Hardening: injection tests, long inputs, rate limits, Dockerfile, deploy backend | Responsive/a11y pass, empty/error states, deploy frontend | Public demo URL works on phone |

## Cut list (in order, if behind)
Portfolio phrasing clusters → printable report styling → optional classifier → copilot memory → dark mode.
Never cut: OCR, citation guard, verifier, review loop, eval page.

## Definition of done (every day)
`pytest -q` green, `npm run build && npm run lint` green, eval smoke (fake LLM) green, screenshots at 1440 and
390 px for changed screens, `docs/PROGRESS.md` updated with what shipped, what didn't, and why.
