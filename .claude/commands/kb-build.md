---
description: Rebuild the knowledge base from the five PDFs and check its quality gates
---
1. `cd backend && python -m claimguard.kb build` (add `--doc <ID>` to rebuild one document).
2. `python -m claimguard.kb check` (spot checks must be 20/20).
3. Open knowledge/build/report.md. Summarise: pages per method, OCR confidence, clauses per document, untagged
   and low-confidence clauses, excluded pages with reasons.
4. If any quality gate in docs/KNOWLEDGE_BASE.md fails, stop and explain; do not "fix" by editing clause text.
   Corrections go in knowledge/overrides/.
$ARGUMENTS
