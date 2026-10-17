# Architecture

## Repository layout
```
claimguard/
├── CLAUDE.md  AGENTS.md  README.md
├── .claude/commands/        next-day.md, eval.md, kb-build.md
├── .agent/rules/            claimguard.md  (Antigravity workspace rules)
├── config/settings.toml     providers, models, thresholds, paths
├── knowledge/
│   ├── pdfs/                the five official PDFs (committed)
│   ├── sources.yaml         doc registry (id, file, regulator, title, url, language pages)
│   ├── overrides/           tags.yaml, scope.yaml, clause_fixes.yaml (human edits, survive rebuilds)
│   ├── checks/spot_checks.yaml
│   └── build/               generated: pages.parquet, clauses.json, chunks.parquet, lancedb/, bm25.pkl,
│                            page_images/, report.md   (git-ignored except report.md)
├── backend/
│   ├── pyproject.toml
│   ├── claimguard/
│   │   ├── config.py
│   │   ├── kb/              ingest.py, ocr.py, vision.py, script_detect.py, segment.py, tagger.py,
│   │   │                    xref.py, index.py, build.py, store.py
│   │   ├── retrieval/       bm25.py, dense.py, fusion.py, rerank.py, filters.py
│   │   ├── agents/          normalise.py, extract.py, rule_extract.py, merge.py, judge.py,
│   │   │                    verify.py, verifier.py, rewrite.py, calibrate.py, pipeline.py, copilot.py
│   │   ├── llm/             client.py (OpenAI-compatible, fallback), prompts/*.md, schemas.py, fake.py
│   │   ├── learning/        feedback.py, memory.py (few-shot store), stats.py, classifier.py, report.py
│   │   ├── eval/            datasets.py, metrics.py, run.py, ablations.py
│   │   ├── api/             main.py, routes_audit.py, routes_ask.py, routes_review.py,
│   │   │                    routes_kb.py, routes_eval.py, sse.py
│   │   └── db.py            SQLite (SQLModel)
│   └── tests/
├── frontend/                React + Vite + TS + Tailwind + TanStack Query + React Router
│   └── src/{api,components,screens,styles}
├── data/
│   ├── samples/             fictional listings, captions, pack images
│   └── gold/                dev.jsonl, holdout.jsonl (never tuned on), labels_b.jsonl (second labeller)
└── docs/                    this folder
```

## Runtime components
| Component | Tech | Notes |
|---|---|---|
| API | FastAPI + Uvicorn | SSE for audit progress |
| App DB | SQLite via SQLModel | tables: audits, flags, feedback, runs, eval_runs, chat_sessions |
| Vector store | LanceDB (on disk) | ~1–3k chunks |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5` | CPU ONNX |
| BM25 | rank_bm25 | pickled |
| OCR | RapidOCR (onnxruntime) | page images at 200 dpi for OCR, 150 dpi for UI |
| Vision | Gemini Flash (image input) | infographic pages, pack images; optional |
| LLM | Groq (Llama 3.3 70B) primary, Gemini Flash fallback; per-step model config | JSON mode |
| Frontend | React 18, Vite, TS, Tailwind, TanStack Query, React Router, Recharts | |
| Deploy | Backend: Hugging Face Spaces (Docker) or Render; Frontend: Vercel/GitHub Pages | public demo = fictional data |

## Data model (SQLite)
- `audits(id, created_at, input_type, surface, category, brand, paid, text, image_path, mode, latency_ms, tokens_in, tokens_out, cost_usd)`
- `claims(id, audit_id, text, start, end, claim_type, alt_types, source[llm|rule|both], qualifier, source_date)`
- `flags(id, audit_id, claim_id, risk, reason, rewrite, confidence, verifier_note, status[open|accepted|dismissed|escalated], reviewer_risk, reviewer_note)`
- `citations(id, flag_id, clause_id, quote, rank)`
- `feedback(id, flag_id, action, from_risk, to_risk, reason_code, note, reviewer, created_at)`
- `runs(id, audit_id, step, model, prompt_hash, input_json, output_json, ms, tokens_in, tokens_out, error)`
- `eval_runs(id, created_at, set_name, config_json, metrics_json, report_path)`

## Config (`config/settings.toml`)
```toml
[llm]
primary = "groq"            # groq | gemini | openai
fallback = "gemini"
extract_model = "llama-3.3-70b-versatile"
judge_model = "llama-3.3-70b-versatile"
verifier_model = "gemini-2.5-flash"
vision_model = "gemini-2.5-flash"
[retrieval]
bm25_k = 30
dense_k = 30
rrf_k = 60
rerank_top = 15
final_k = 5
[thresholds]
min_quote_chars = 20
low_ocr_conf = 0.80
copilot_min_score = 0.35
[app]
public_demo = true          # fictional samples only, real uploads disabled
max_input_chars = 20000
```
Keys only from environment: `GROQ_API_KEY`, `GEMINI_API_KEY`. `.env` is git-ignored.
