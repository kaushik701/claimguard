# Workspace rules (Antigravity)

Follow AGENTS.md and CLAUDE.md in the repo root; they are the source of truth. You own `frontend/` only.
- Build from docs/SPEC.md (screens), docs/DESIGN_TOKENS.md (look), docs/API_CONTRACT.md and
  `frontend/src/api/openapi.json` (data). Never change the contract; propose changes in docs/PROGRESS.md.
- Until the contract is frozen (end of Day 2), use mocks in `frontend/src/api/mock/`.
- Work one docs/days/DAY-N.md at a time, Antigravity section only.
- Every screen: loading, empty, error states; works at 1440 and 390 px; keyboard and visible focus; risk shown
  with text, not colour alone; quotes in serif with document and page.
- Before finishing: `npm run build && npm run lint`, Vitest, Playwright smoke; screenshots to
  docs/screenshots/day-N/.
