# Day 0: Scaffold, config, LLM client

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code (backend)
1. Create the layout in docs/ARCHITECTURE.md. `backend/pyproject.toml` (python 3.12): fastapi, uvicorn, sqlmodel,
   pydantic>=2, pymupdf, rapidocr-onnxruntime, fastembed, lancedb, rank_bm25, pyarrow, openai, httpx,
   wordfreq, scikit-learn, python-multipart, sse-starlette, pytest, ruff.
2. `config.py` loads `config/settings.toml` + env keys; `public_demo` flag.
3. `llm/client.py`: OpenAI-compatible client for groq/gemini/openai; `json(system, user, schema)` with Pydantic
   validation, 2 retries (error text fed back only after a validation error), provider fallback on 429/timeout,
   usage counters (calls, tokens, ms, fallbacks), prompt hash logging.
4. `llm/fake.py`: FakeLLM that returns recorded fixtures by prompt name + input hash; used in all tests.
5. `llm/prompts/*.md` copied from docs/prompts/SYSTEM_PROMPTS.md (one file per prompt) + loader that fills
   placeholders and wraps untrusted input.
6. `db.py` with the tables in docs/ARCHITECTURE.md.
7. `.github/workflows/ci.yml`: ruff, pytest (no network), frontend build.
## Antigravity (frontend)
1. Vite + React + TS + Tailwind + React Router + TanStack Query + Recharts. Tokens from docs/DESIGN_TOKENS.md
   as CSS variables, light/dark.
2. App shell: header (name, demo badge, "not legal advice"), left nav (Audit, Pre-flight, Ask, Review,
   Portfolio, Knowledge, Eval, Settings) collapsing to a bottom bar at 390 px.
3. `src/api/client.ts` with a mock adapter (`src/api/mock/*.json`) switchable by `VITE_USE_MOCKS`.
4. Shared components stubs: RiskPill, StatTile, EmptyState, ErrorBanner.
## Tests
- test_llm_client: valid JSON, invalid JSON then valid, 429 → fallback, no key → clear error.
- test_prompt_loader: untrusted input wrapped; placeholders all filled.
## Done when
`pytest -q` green with no network; `npm run build && npm run lint` green; screenshot of the shell at 1440/390.
