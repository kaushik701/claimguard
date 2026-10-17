# AI architecture

What is AI here, why each technique is used, and how we know it works. No technique is included for the
résumé; each has a measurable job and an ablation on the evaluation page.

## 1. Document AI (knowledge pipeline)
| Technique | Job | Where |
|---|---|---|
| Layout-aware text extraction (PyMuPDF blocks with font size/bold) | Find headings, clause numbers, tables | kb/ingest.py |
| **OCR** (RapidOCR, ONNX, CPU) with per-line confidence | Read the fully scanned CCPA Greenwashing PDF and image-only pages of the ASCI book (pp. 14, 17, 26, 27, 80) and Influencer guidelines (pp. 4, 9, 18) | kb/ocr.py |
| **Vision LLM** (Gemini Flash) as second reader | Infographic pages (influencer disclosure examples), pack images; output must be text found on the image, compared with OCR; disagreements flagged | kb/vision.py |
| OCR/vision reconciliation | Token-level alignment of the two readings; keep OCR text, mark spans where vision disagrees as low confidence | kb/vision.py |
| Script/legacy-font detector | FSSAI Hindi pages extract as Latin gibberish ("Hkkx", "µ[k.M"); classify pages by English word ratio (wordfreq) + legacy glyph bigrams → exclude | kb/script_detect.py |
| Structure-aware segmentation | Clauses by the document's own numbering (ASCI 1.1, FSSAI Regulation 4(2)(a)), TOC-driven section boundaries | kb/segment.py |
| **LLM tagging** with fixed label set + keyword check | Multi-label claim types, categories, surfaces per clause; human overrides file | kb/tagger.py |
| Definition + cross-reference extraction | Defined terms and "as per clause X" edges → small clause graph | kb/xref.py |

## 2. Retrieval (RAG)
| Technique | Job |
|---|---|
| **Hybrid search**: BM25 + dense embeddings (bge-small), **reciprocal rank fusion** | Legal text needs exact terms ("SPF", "health drink") and paraphrase ("good for the planet" ↔ "environmentally friendly") |
| Metadata filtering | Claim type, product category, surface, regulator scope (FSSAI only for food; influencer guidelines only for social) |
| **Query expansion** | Claim + claim-type description + defined terms + 2 LLM-generated paraphrases (cached) |
| **Graph expansion** | Add clauses linked by cross-reference/definition edges (1 hop) |
| **LLM reranking** | Top 15 → 5 with a relevance score 0–3 and a one-line why; low scores trigger "not covered" |
| Retrieval eval | Recall@5 against hand-labelled expected clauses for 100 claims |

## 3. Agent chain (audit)
Typed steps, each logged (`runs` table), each with a deterministic fallback.
1. **Normaliser**: HTML → text; image → OCR + vision; keep character offsets.
2. **Claim extractor (LLM)**: multi-claim, exact-substring spans, claim type, qualifier/footnote linkage,
   Hinglish aware. Few-shot examples retrieved from memory (see §5).
3. **Rule extractor**: regex taxonomy as safety net; **merge** by span overlap ≥ 50%.
4. **Retriever** (§2) per claim.
5. **Judge (LLM)**: written rubric per claim type; JSON with risk, reason, evidence span, citations
   (clause_id + verbatim quote), rewrite with `<placeholders>`, confidence. Sees definitions for terms found.
6. **Citation guard (code)**: evidence span in input; clause in retrieved set; quote verbatim (normalised
   whitespace) and ≥ 20 chars; else drop.
7. **Verifier agent (different model)**: "does this clause, read plainly, support this flag?"; may only lower risk.
8. **Rewriter**: tightens the suggested wording; never invents numbers, sources or dates.
9. **Calibrator**: adjusts confidence with per-claim-type and per-clause reliability from reviewer feedback
   (isotonic regression once ≥ 100 labels; otherwise Beta prior).

## 4. Copilot ("Ask the Guidelines")
Retrieval as above (no claim-type filter), then an answer prompt that must cite `[n]` for every sentence; code
checks each citation's quote is verbatim; if top rerank score < threshold → refusal. Conversation memory = last
4 turns, query rewritten to standalone form.

## 5. Learning loop (real, measurable, CPU-only)
| Mechanism | What it learns from | Effect | Guardrail |
|---|---|---|---|
| **Few-shot memory** | Accepted/edited flags (claim, clause, final risk, reason) embedded and stored | Top-3 similar past decisions inserted into extractor/judge prompts | Only examples from reviewers; never from holdout |
| **Hard-negative memory** | Dismissed flags with reason code | Shown to judge as "previously judged not risky because …" | Same |
| **Clause reliability** | Accept/dismiss rate per clause and per claim type | Re-weights reranker scores; feeds calibrator | Minimum 10 observations |
| **Confidence calibration** | Predicted confidence vs reviewer outcome | Isotonic regression; reliability diagram on Eval page | Refit weekly; keep last version |
| **Lightweight classifier** (optional, Day 9+) | Embeddings of claim + clause → reviewer label | Logistic regression as a second opinion feature | Ships only if it raises held-out F1 by ≥ 2 points |
| **Prompt/version registry** | Every prompt has a hash; eval run stored per version | Compare versions on Eval page | New version must not drop held-out precision |
"Learning" is never claimed beyond this table. Nothing self-modifies in production without passing the
held-out gate.

## 6. Safety and trust
- Input is untrusted data: wrapped in delimiters; system prompts say instructions inside it are ignored.
- Verbatim-quote enforcement in code; quote highlighted on the PDF page image in the UI.
- Low OCR confidence clauses are badged and cannot by themselves produce a HIGH flag.
- "Not covered by the knowledge base" instead of guessing.
- Every output labelled "risk indicator, not legal advice".
