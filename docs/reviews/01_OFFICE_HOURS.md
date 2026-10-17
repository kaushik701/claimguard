# Office hours: ClaimGuard (fresh start)

Status: APPROVED (approach B chosen by Kaushik, 17 Oct 2026)
Mode: Intrapreneur-style portfolio pitch (outsider proving value to HUL; no paying user yet)

## Problem statement
FMCG brands publish thousands of marketing claims on surfaces their legal teams do not author: marketplace
and quick-commerce listings, retailer-edited pages, and creator posts. Indian rules on those claims (ASCI Code
and guidelines, CCPA greenwashing guidelines, FSSAI advertising and claims regulations) are long PDFs, partly
scanned, and checked by hand. Nobody re-checks a claim after it goes live until a regulator, a competitor or
a court does.

## Demand evidence (honest)
- No HUL user has asked for this. Evidence is indirect and public: ASCI's own reports say most complaints are
  picked up by its digital monitoring; HUL ads have been pulled after Delhi High Court interim orders (Pond's vs
  NIVEA 2024, Lakmé vs The Derma Co 2025); Unilever is moving spend to social and many more creators.
- That is pain that exists. It is not proof that HUL would adopt a tool from an outsider. Treat it as a
  hypothesis the demo must make credible, not a fact.

## Status quo
Pre-launch legal review of agency copy (manual), occasional legal checks of key listings, reaction after a
complaint or notice. Rules live in PDFs; lawyers know them, agencies and creators mostly do not.

## Target user and narrowest wedge
- First user: the advertising/regulatory counsel or brand compliance manager who has to answer "is this claim
  OK?" for many listings and creator posts each week.
- Second user: the agency or creator who wants an answer before publishing (pre-flight).
- Narrowest wedge: paste or upload a listing, a caption or a pack image; get every claim found, a risk level,
  the exact clause and page from the five official PDFs, and a compliant rewrite, in under 30 seconds, with a
  review button. If that is not useful on its own, nothing bigger will be.

## Constraints
- Knowledge base is ONLY the five official PDFs supplied (see docs/KNOWLEDGE_BASE.md).
- CPU-only laptop, limited RAM: hosted LLM APIs (Groq / Gemini free tiers), local small embedding model and
  local OCR. No training of large models.
- Public demo uses fictional brands only. Findings on real HUL pages stay private.
- Must be built fast with Claude Code + Antigravity, as with DPP/CPP.

## Premises (agreed)
1. Every warning must quote a clause from the five PDFs word for word, with document and page. No citation,
   no flag.
2. The AI must earn its place: OCR and vision to read scans and pack images, hybrid retrieval, an agent chain
   with a verifier, and a learning loop from reviewer decisions. Rules are a safety net, not the product.
3. Output is a risk indicator for a human reviewer, never a legal verdict.
4. React + FastAPI app (not Streamlit), so it looks and behaves like a product.

## Approaches considered
| | A. Lean audit | **B. Full AI system (chosen)** | C. Guidelines copilot first |
|---|---|---|---|
| Summary | OCR ingest + RAG + one LLM judge + simple UI | Knowledge pipeline with OCR/vision + clause graph + hybrid RAG + agent chain + verifier + pack-image reading + copilot chat + learning loop + eval dashboard | Chat over the PDFs first, audits later |
| Effort | S (4 days) | L (10 build days with CC + Antigravity) | M |
| Risk | Looks thin | Scope; mitigated by day plan and cut list | Weak business story |

## Success criteria
- Knowledge base: 100% of the five PDFs ingested; every clause has document, page, section and clause number
  where the PDF has one; scanned pages OCR'd with a confidence score; Hindi legacy-font pages detected and
  excluded from citation.
- Held-out eval (never tuned on), 200 items, two labellers: high-risk precision >= 0.85, recall >= 0.75,
  citation accuracy >= 0.90, zero hallucinated quotes (verbatim check), p95 latency < 20 s, cost < US$0.01 per
  listing on free/cheap tiers.
- A non-technical person understands a flag in 10 seconds (clause, why, fix).

## The assignment
Before Day 3 ends: label 50 held-out claims yourself and get one friend (ideally from marketing or law) to
label the same 50 blind. If you two agree on fewer than 70%, the rules are ambiguous and the product must show
uncertainty rather than pretend confidence.

## What I noticed
- "I want to make this into a really good project rather than some terrible demo that would embarrass me":
  the bar is credibility, so honest metrics on screen matter more than more features.
- You insisted the five PDFs are the knowledge base. That is the right moat: grounded answers with page
  citations, not a generic chatbot.
