# Knowledge base: the five official PDFs

These five files are the ONLY source of truth. Every flag and every copilot answer must quote one of them
word for word, with document and page. Files live in `knowledge/pdfs/` and are registered in
`knowledge/sources.yaml`.

| ID prefix | File | Regulator | Pages | What it is | Reading method (measured) |
|---|---|---|---|---|---|
| `ASCI` | ASCI_Codes_Guidelines_Book.pdf | ASCI | 82 | Code (Chapters I–IV) + category guidelines (F&B, disclaimers, new/improved, large pack, fairness, celebrities, awards/rankings, influencers, gender stereotypes, deceptive design, etc.) | Text layer on 77 pages; **5 image-only pages (14, 17, 26, 27, 80)** → OCR + vision |
| `ASCI-INF` | ASCI-Guidelines-Influencer-Advertising-In-Digital-Media-1.pdf | ASCI | 18 | Influencer disclosure rules, labels, placement by platform | Text layer partial, **63 embedded images; pages 4, 9, 18 image-only** → OCR + vision (infographics) |
| `ASCI-GREEN` | Guidelines-for-Advertisements-Making-Environmental-Green-Claims.pdf | ASCI | 3 | Environmental / green claims | Clean text |
| `CCPA-GW` | Greenwashing_Guidelines.pdf | CCPA (Govt. of India) | 6 | Guidelines for Prevention and Regulation of Greenwashing or Misleading Environmental Claims, 2024 | **Fully scanned (0 text chars)** → OCR required on every page |
| `FSSAI` | Gazette_Notification_Advertising_Claims_27_11_2018.pdf | FSSAI | 32 | Food Safety and Standards (Advertising and Claims) Regulations, 2018 (gazette) | Bilingual. **English on pages 1, 20–32**; Hindi pages 2–19 are in a legacy font that extracts as Latin gibberish (e.g. "Hkkx IIIµ[k.M") → detect and exclude |

## What gets built from them (`python -m claimguard.kb build`)
1. **Page records**: for every page: text layer, OCR text (if needed), OCR mean confidence, page image (PNG,
   150 dpi, for the UI), language/script flag (`en`, `hi_unicode`, `hi_legacy`, `image_only`).
2. **Clauses**: segmented on the document's own structure:
   - ASCI book: Chapter > numbered clause (1.1, 1.2 …) > sub-clause (a)(b); guideline sections by their title
     in the table of contents (page numbers from the TOC are used to set section boundaries).
   - FSSAI: Regulation number > sub-regulation (1)(2) > clause (a)(b); Schedules as their own sections.
   - CCPA-GW: numbered paragraphs from OCR text; if a number cannot be read, ID uses title + page, never a guess.
   - Each clause: `clause_id`, `doc_id`, `regulator`, `section_path` (e.g. "Chapter I > 1.2"), `number`,
     `title`, `text`, `page_start`, `page_end`, `source` (`text`|`ocr`|`vision`), `ocr_conf`, `hash`.
3. **Chunks** for retrieval: one clause = one chunk if under 350 tokens, else split on sentences with the
   section path prepended. Each chunk keeps its `clause_id`.
4. **Tags** (multi-label): claim types it governs (efficacy, comparative, leadership, time_bound, appearance,
   scientific, environmental, natural_purity, nutrition_health, disclosure, puffery, pricing_offer,
   celebrity_endorsement, awards_rankings, children, gender), product categories (all / food / beauty /
   personal / home), surfaces (all / social / ecommerce …). Tagged by an LLM with a fixed label set, checked by
   keyword rules, and editable in `knowledge/overrides/tags.yaml` (survives rebuilds).
5. **Definitions index**: defined terms (e.g. FSSAI "claim", "health claim"; ASCI "advertisement",
   "influencer") so prompts can include the definition when the term appears.
6. **Cross-references**: "as per clause 1.2", "Regulation 4(2)" links stored as graph edges, so retrieving a
   clause can pull the clause it depends on.
7. **Vectors** (LanceDB) and **BM25 index** over chunks.
8. **Build report** `knowledge/build/report.md`: pages per method, OCR confidence histogram, clauses per doc,
   untagged clauses, low-confidence clauses. Reviewed by a human once per build.

## Quality gates for a build (fail the build if not met)
- Every page accounted for (text / OCR / vision / excluded-with-reason).
- No clause from a `hi_legacy` page.
- CCPA-GW yields >= 8 clauses with mean OCR confidence >= 0.85, else flagged for manual check.
- Spot-check file `knowledge/checks/spot_checks.yaml`: 20 known sentences (copied by hand from the PDFs) must be
  found verbatim in the clause store.

## Not in the knowledge base (UI must say so)
CCPA Misleading Advertisements Guidelines 2022, Legal Metrology (Packaged Commodities) Rules, Drugs and
Magic Remedies Act, Cosmetics rules. A claim that needs them is reported as "not covered by the knowledge base".
Adding a document later = drop the PDF in `knowledge/pdfs/`, add an entry to `sources.yaml`, rebuild.
