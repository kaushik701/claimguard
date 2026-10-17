# ClaimGuard — instructions for Claude Code

AI regulatory claims-risk auditor for Indian FMCG marketing, grounded ONLY in five official PDFs (ASCI Code &
Guidelines book, ASCI Influencer guidelines, ASCI Green-claims guidelines, CCPA Greenwashing guidelines 2024,
FSSAI Advertising & Claims Regulations 2018). Outputs are risk indicators for reviewers, not legal advice.

@AGENTS.md
@docs/BUILD_PLAN.md
@docs/PROGRESS.md

Read when relevant (not every turn):
- docs/SPEC.md (screens), docs/WORKFLOW.md (plain language), docs/ARCHITECTURE.md (layout, data model, config)
- docs/ai/AI_ARCHITECTURE.md (OCR, RAG, agents, learning), docs/prompts/SYSTEM_PROMPTS.md (all prompts)
- docs/KNOWLEDGE_BASE.md (the PDFs, page facts, build gates), docs/EVAL_PLAN.md, docs/API_CONTRACT.md
- docs/reviews/ (office hours, CEO and engineering reviews: decisions are locked there)
- docs/days/DAY-N.md (today's work)

## How we work
- One day file at a time. Use `/next-day`. Plan first, wait for Kaushik's OK, then build.
- You own `backend/`, `knowledge/`, `data/`, `.github/`. Antigravity owns `frontend/`. Do not edit `frontend/`
  except `frontend/src/api/openapi.json` on Day 2 (contract export).
- Tests use FakeLLM and recorded fixtures; no network in tests. Real-model runs are manual and their reports are
  committed.
- After every change in backend: `cd backend && pytest -q`. Before finishing a day: eval smoke + PROGRESS.md.
- When a metric changes, explain in PROGRESS.md which items moved and why.
