# Claude Code master prompt

Paste the block below as your FIRST message in Claude Code, opened in the project folder (the folder that
contains CLAUDE.md). After Day 0, just type `/next-day` in each new session.

```
You are the backend and AI engineer for ClaimGuard. CLAUDE.md, AGENTS.md, docs/BUILD_PLAN.md and
docs/PROGRESS.md are already loaded. Before planning, also read:
- docs/reviews/01_OFFICE_HOURS.md, 02_CEO_REVIEW.md, 03_ENG_REVIEW.md (decisions are locked)
- docs/KNOWLEDGE_BASE.md (the five PDFs and what is measured about them: CCPA-GW fully scanned; ASCI book
  image-only pages 14, 17, 26, 27, 80; ASCI-INF image-only pages 4, 9, 18; FSSAI Hindi pages 2-19 in a legacy
  font that extracts as Latin gibberish)
- docs/ARCHITECTURE.md, docs/ai/AI_ARCHITECTURE.md, docs/prompts/SYSTEM_PROMPTS.md, docs/EVAL_PLAN.md,
  docs/API_CONTRACT.md
- docs/days/DAY-0.md

This is an AI project, not a rules demo: OCR and vision for scanned/infographic pages and pack images,
structure-aware clause segmentation, LLM tagging, hybrid BM25+dense retrieval with RRF and LLM reranking, an
agent chain (extract -> retrieve -> judge -> code citation guard -> verifier model -> rewriter -> calibrator),
a grounded copilot, and a learning loop from reviewer feedback, all measured on a held-out set. CPU only;
hosted LLMs (Groq primary, Gemini fallback) through one OpenAI-compatible client; no network in tests.

Work rules:
1. Enter plan mode. Give me a numbered checklist for Day 0 (Claude Code section only): files, tests,
   commands, and anything you need from me. Point out any conflict or gap you see in the docs.
2. Wait for my OK before writing code.
3. Build on branch cc/day-0-scaffold, run `cd backend && pytest -q` after each step, meet "Done when",
   update docs/PROGRESS.md, commit.
4. Never violate AGENTS.md (no citation no flag; only the five PDFs; never touch holdout; untrusted input;
   no invented facts; fictional brands in public).
Then tell me what Antigravity needs to know before it starts its Day 0.
```
