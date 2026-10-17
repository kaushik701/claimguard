# CEO review: ClaimGuard (mode: SELECTIVE EXPANSION)

Hold the core scope, add only what makes it obviously a product and obviously AI.

## The 10-star version (for the roadmap slide, not the build)
A compliance co-pilot that watches every live claim of a brand across marketplaces, quick-commerce apps,
brand sites and creator posts, reads pack images, knows every Indian rule with page citations, tells the
agency before publishing, alerts legal when a live claim drifts or a rule changes, and learns from each
lawyer's decision.

## What we build now (in scope)
1. **Knowledge pipeline** over the five PDFs: text extraction, OCR for scanned pages, vision reading of
   infographic pages, legacy-Hindi detection, clause segmentation, clause graph (section > clause > sub-clause,
   cross-references, definitions).
2. **Audit**: listing text, caption, or pack image in; claims out with risk, clause quote + page, rewrite.
3. **Pre-flight** for agencies/creators (same engine, verdict-first UI).
4. **Ask the Guidelines**: a grounded Q&A copilot over the five PDFs, every answer cited with page, refuses
   when the PDFs do not cover the question.
5. **Review loop**: accept / dismiss / edit risk, with reasons; decisions become labelled examples.
6. **Portfolio view** across audited listings.
7. **Evaluation page**: live metrics from the held-out set and reviewer agreement. Honesty is a feature.
8. **Knowledge explorer**: browse clauses, see the PDF page next to the extracted text and OCR confidence.

## Expansions accepted (cheap, high signal)
- Pack-image claim reading (front-of-pack photo -> OCR/vision -> claims). Many FMCG claims are on the pack.
- Hinglish claim handling in prompts ("100% zyaada", "germ-free ghar").
- Printable audit report (HTML/PDF) a manager can forward.

## Expansions rejected (and why)
- Live scraping of Amazon/Flipkart/Blinkit: terms of service and reputational risk. Upload or paste only.
- Fine-tuning an LLM: no GPU, no labelled data yet. A small classifier trained on reviewer labels is allowed
  later (CPU, scikit-learn) and only after it beats the baseline on the held-out set.
- Multi-tenant login, billing: not needed to prove value.
- Rules from sources other than the five PDFs (CCPA 2022, Legal Metrology): out until the PDFs are supplied.
  The UI says "not in knowledge base" instead of guessing.

## Positioning (what we say to HUL)
- HUL already uses AI for media mix, shelf images, retailer ads and content generation. ClaimGuard covers the
  part after publishing: is what is live still compliant, and can we prove it with the rule and page.
- Ask: one category, one quarter, legal reviews 200 flags; measure hours saved per 100 listings and agreement.
- Never claim HUL lacks this internally; say "not publicly evidenced".

## Risks
| Risk | Mitigation |
|---|---|
| Hallucinated rules or quotes | Verbatim quote check against the clause store; verifier agent; refusal path |
| OCR errors on the scanned CCPA PDF | OCR confidence per line; low-confidence clauses badged "check against PDF"; page image shown beside text |
| Looks like a demo | React app, real data flows, eval page with honest numbers, printable report |
| Scope creep | Day plan with a cut list; anything not in docs/BUILD_PLAN.md waits |
| Defamation | Fictional brands in public; real findings private |
