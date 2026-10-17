# Antigravity master prompt

Open the same project folder in Antigravity. Use Planning mode. Paste the block below as the first task.
Antigravity can run several agents from its Agent Manager; the block sets up three that work in parallel on
`frontend/` only.

```
You are the frontend team for ClaimGuard, an AI regulatory claims-risk auditor for Indian FMCG marketing.
Read AGENTS.md, .agent/rules/claimguard.md, docs/SPEC.md, docs/DESIGN_TOKENS.md, docs/API_CONTRACT.md,
docs/WORKFLOW.md, docs/BUILD_PLAN.md, docs/PROGRESS.md and docs/days/DAY-0.md. You own frontend/ only.

Stack: React 18 + Vite + TypeScript + Tailwind + React Router + TanStack Query + Recharts. Tokens from
docs/DESIGN_TOKENS.md as CSS variables (light + dark). Fonts: IBM Plex Sans, IBM Plex Mono, Source Serif 4.
Until the API contract is frozen (end of Day 2) use mock data in frontend/src/api/mock/ behind
VITE_USE_MOCKS=true. After that, generate types from frontend/src/api/openapi.json and never edit it.

Product rules you must show in the UI:
- Every warning shows the rule quote (serif), document, section, clause number and PDF page, plus "Open page"
  (page image with the quote highlighted). OCR-read clauses get a "read by OCR, check the page" badge.
- Risk is shown as text plus colour. "Risk indicators, not legal advice" in the header.
  Public demo shows a "demo · fictional brands" badge.
- Claims not covered by the knowledge base are listed separately, never shown as safe.
- Every screen has loading, empty and error states and works at 1440 px and 390 px with keyboard support.

Agents:
- Agent A (shell + Audit): app shell and nav, Audit screen (input tabs, SSE progress, claim highlighter,
  flag list, FlagCard, CitationBlock, PageViewer, RewriteDiff, ConfidenceBar, keyboard j/k/a/d/e), Pre-flight.
- Agent B (knowledge + ask): Knowledge explorer (documents, clause browser, clause detail with page image, tag
  editor), Ask the Guidelines chat with citations and refusals.
- Agent C (review + insights): Review queue, Portfolio (heatmap, breakdowns, phrasing clusters, trend),
  Evaluation (metric tiles vs targets, run history, confusion by type, ablations, reliability diagram),
  Settings.

Each agent: follow the Antigravity section of the current docs/days/DAY-N.md only; plan first and show me the
plan; then build; use the browser to screenshot changed screens at 1440 and 390 px into
docs/screenshots/day-N/; run `npm run build && npm run lint` and tests; add a short entry to
docs/PROGRESS.md. Start with Day 0: Agent A builds the shell and tokens first; B and C start after the shell
is merged.
```
