# ClaimGuard

AI regulatory claims-risk auditor for Indian FMCG marketing. It reads a listing, caption or pack image, finds
every claim, checks it against five official rulebooks (ASCI Code & Guidelines, ASCI Influencer and
Green-claims guidelines, CCPA Greenwashing guidelines 2024, FSSAI Advertising & Claims Regulations 2018), and
returns risk, the exact clause with its page, and compliant wording. Every warning quotes its rule word for
word, or it is not shown.

> Risk indicators for reviewers, not legal advice. Not affiliated with or endorsed by Hindustan Unilever,
> Unilever or any brand owner. The public demo uses fictional brands.

## Status
Build kit only. Code is built day by day with Claude Code (backend, AI, knowledge base) and Antigravity
(frontend). See `docs/PROGRESS.md`.

## Start here
| You want to | Read |
|---|---|
| Understand it in 2 minutes | docs/WORKFLOW.md |
| See why it's built this way | docs/reviews/ (office hours, CEO review, engineering review) |
| Start building with Claude Code | docs/prompts/CLAUDE_CODE_MASTER_PROMPT.md, then `/next-day` |
| Start building with Antigravity | docs/prompts/ANTIGRAVITY_MASTER_PROMPT.md |
| Screens | docs/SPEC.md, docs/DESIGN_TOKENS.md |
| AI design | docs/ai/AI_ARCHITECTURE.md, docs/prompts/SYSTEM_PROMPTS.md |
| Knowledge base | docs/KNOWLEDGE_BASE.md, knowledge/sources.yaml |
| How it's measured | docs/EVAL_PLAN.md |

## Results
Filled in from the first real held-out run (Day 8).
