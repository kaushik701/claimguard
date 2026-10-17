# Engineering review: ClaimGuard

Reviewed against docs/ARCHITECTURE.md and docs/ai/AI_ARCHITECTURE.md. Decisions below are locked unless a
day file says otherwise.

## Architecture decisions
| # | Decision | Why |
|---|---|---|
| E1 | Monorepo: `backend/` (Python 3.12, FastAPI), `frontend/` (React + Vite + TypeScript + Tailwind), `knowledge/` (PDFs + built artefacts) | Two agents can work in parallel with one contract |
| E2 | API contract in `docs/API_CONTRACT.md`, generated `openapi.json` frozen on Day 2 | Antigravity builds UI against it without touching backend |
| E3 | Storage: SQLite (app data) + LanceDB on disk (vectors) + JSON/Parquet artefacts for clauses | Zero servers, fits in RAM, easy to ship |
| E4 | Embeddings: `BAAI/bge-small-en-v1.5` via fastembed (ONNX, CPU, ~130 MB) | Free, local, fast enough for ~1–2k chunks |
| E5 | Retrieval: hybrid BM25 + dense, reciprocal-rank fusion, metadata filters (claim type, category, surface, regulator), then LLM rerank of top 15 → 5 | Legal text needs exact terms (BM25) and paraphrase (dense) |
| E6 | OCR: RapidOCR (ONNX, CPU) for scanned pages; Gemini Flash vision as second reader for infographic pages and pack images; keep both outputs and confidence | Local first, vision only where needed |
| E7 | LLM access via one client (OpenAI-compatible) with provider fallback Groq → Gemini; JSON-schema outputs validated by Pydantic; retries | Free tiers rate-limit |
| E8 | Agent chain is plain Python (no framework) with typed steps; each step logs inputs/outputs to `runs` table | Debuggable, testable, cheap |
| E9 | "No citation, no flag" enforced in code (`verify.py`), not prompts | Prompts can be ignored; code cannot |
| E10 | Deterministic rule engine kept as baseline and safety net | Lets us prove the AI adds value |
| E11 | Learning loop: reviewer decisions → `feedback` table → (a) few-shot example store retrieved by similarity, (b) per-clause reliability stats, (c) weekly calibration of confidence, (d) optional CPU classifier gated by held-out eval | Real learning without GPUs, measurable |
| E12 | Fake LLM + recorded fixtures for all tests; no network in CI | Fast, reproducible |

## Data flow (audit)
```
input (text | html | image) ─► normalise ─► [image] OCR + vision ─► text with spans
   ─► claim extractor (LLM, multi-claim, exact spans)  ∥  rule extractor (regex safety net) ─► merge
   ─► per claim: hybrid retrieve (filters) ─► LLM rerank ─► top-5 clauses
   ─► judge (rubric, JSON: risk, reason, evidence span, citations[clause_id, quote], rewrite, confidence)
   ─► verify (code): span in input? clause retrieved? quote verbatim in clause? else drop
   ─► verifier agent (LLM): does clause support flag? can only lower risk
   ─► calibrate confidence (feedback stats) ─► persist audit + flags ─► UI
```

## Failure modes and handling
| Failure | Handling | Test |
|---|---|---|
| LLM returns invalid JSON | Pydantic validation, 2 retries with error text, then rule-engine fallback with banner | test_llm_invalid_json |
| Provider 429/timeout | Retry once, switch provider, record `fallbacks` | test_provider_fallback |
| Quote not verbatim | Flag dropped, reason logged, shown in "dropped" panel | test_verify_drops_paraphrase |
| OCR low confidence | Clause marked `ocr_low_conf`; UI badge; excluded from auto-high unless rule engine agrees | test_ocr_conf_flag |
| Hindi legacy-font page | Detected (ratio of non-dictionary tokens + known glyph pairs like "Hkkx"), excluded from index | test_legacy_hindi_detect |
| Claim not covered by any clause | Listed as "not covered by the knowledge base", never flagged | test_no_rule_path |
| Prompt injection in listing text ("ignore previous instructions") | Input wrapped as data with delimiters; system prompt says treat as untrusted; verify step still enforces quotes | test_injection_text |
| Huge input | 20k char cap, chunked extraction | test_long_input |

## Test plan
- Unit: ingestion (segmenter, OCR adapter with fixture images, legacy-Hindi detector), retrieval (fusion,
  filters), verify, merge, calibration.
- Contract: every API route against `openapi.json` with schemathesis-lite (pytest + pydantic).
- Golden: 12 fixture listings with expected flags (recorded LLM outputs).
- Eval: `python -m claimguard.eval --set holdout` in CI with the fake LLM on recorded outputs; the real-model
  run is manual and its report is committed.
- Frontend: Vitest for components; Playwright smoke for each screen at 1440 and 390 px.

## Performance budget
- Ingestion of all five PDFs: < 5 min on CPU (OCR dominates; cache per page hash).
- Audit p95 < 20 s with Groq; retrieval < 300 ms; UI first paint < 2 s.

## What I would cut first if late
Portfolio view → printable report → Hinglish few-shots → copilot chat history. Never cut: verify step, eval page,
OCR, review loop.
