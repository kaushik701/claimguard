# Product spec: ClaimGuard

## Users
- **Reviewer** (brand compliance / advertising counsel): audits listings, reviews flags, exports reports.
- **Creator / agency** (pre-flight): checks a draft before publishing.
- **Admin** (you): rebuilds the knowledge base, runs evals.
No login in v1; a "reviewer name" field in settings tags feedback.

## Screens (React). Every screen works at 1440 px and 390 px.

### 1. Audit (home) `/audit`
- Input tabs: **Paste text** | **Upload saved page (HTML/PDF)** | **Pack image** (JPG/PNG) | **Sample** (fictional).
- Context fields: surface (e-commerce, quick commerce, brand site, social post), category (home, beauty,
  personal, food), paid promotion (social only), brand (free text).
- Run button → progress steps shown live (Reading → Finding claims → Finding rules → Judging → Checking) via
  server-sent events.
- Result layout:
  - Stat row: claims found, high, medium, not covered by knowledge base, dropped by checks.
  - Left: input with each claim highlighted by risk (for images: the photo with OCR boxes drawn, plus the text).
  - Right: flag list; selected flag card shows risk pill, claim type, "why", cited clause(s) (document, section
    path, clause number, page, OCR badge if any, quote in serif), **"Open page"** (PDF page image in a drawer
    with the quote highlighted), suggested wording side by side with the original, confidence bar, verifier
    note, reviewer note, Accept / Dismiss / Change risk / Escalate. Keyboard: j/k, a, d, e.
  - Panels: claims not covered by the knowledge base; low-risk claims; dropped flags with reason.
  - Export: CSV, printable report (HTML → print to PDF).

### 2. Pre-flight `/preflight`
- Draft text + format + category + paid toggle. Verdict banner: Revise / Check / No flags (with the caveat
  "no flags is not clearance"). One card per issue with fix. "Copy all fixes".

### 3. Ask the Guidelines `/ask`
- Chat. Each answer: short answer, then numbered citations (document, clause, page, quote). "Open page" per
  citation. Refusal when retrieval confidence is low: "The five guideline documents don't address this."
- Suggested starter questions.

### 4. Review queue `/review`
- All open flags across audits; filters (risk, claim type, regulator, surface, brand, confidence); bulk
  accept/dismiss; sort by confidence (low first = most useful to review).

### 5. Portfolio `/portfolio`
- Brand × claim-type heatmap; flags by regulator and surface; recurring risky phrasings (clustered by
  embeddings); trend of open vs resolved.

### 6. Knowledge explorer `/knowledge`
- Document list with build stats (pages by method, clauses, OCR confidence).
- Clause browser: search, filters by doc/tag; clause detail with page image side by side; tags editable (writes
  to overrides); "used in N flags"; "reviewers agreed X% when this clause was cited".

### 7. Evaluation `/eval`
- Metric tiles vs targets (held-out precision, recall, F1, citation accuracy, hallucinated-quote rate, latency,
  cost/listing), run history table, confusion by claim type, reviewer agreement, ablations (rules only / no
  verifier / no reranker / no few-shot memory).

### 8. Settings `/settings`
- Provider status (Groq/Gemini keys present? last error), model names, reviewer name, knowledge build info.

## Global
- Header: product name, "demo · fictional brands" badge in public mode, "Risk indicators, not legal advice".
- Empty, loading, error states for every screen. Error banner when the LLM is unavailable: "AI unavailable,
  showing rule-based result".

## Out of scope v1
Scraping, auth, multi-tenant, billing, rules outside the five PDFs, fine-tuning LLMs.
