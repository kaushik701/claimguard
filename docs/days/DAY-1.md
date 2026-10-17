# Day 1: Knowledge ingestion: text, OCR, script detection

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. `knowledge/sources.yaml` already lists the 5 PDFs (see docs/KNOWLEDGE_BASE.md). Read it.
2. `kb/ingest.py`: per page → text layer with block font sizes/bold; render page PNG (150 dpi for UI, 200 dpi for
   OCR); classify page: `text`, `image_only` (< 50 chars), `hi_unicode`, `hi_legacy`.
3. `kb/script_detect.py`: legacy-Hindi detector = share of tokens that are English words (wordfreq zipf > 2)
   < 0.35 AND presence of legacy bigrams (e.g. "kk", "Hk", "µ", "[k", "ç") above a threshold. Calibrate on FSSAI
   pages 2–19 (legacy) vs 20–32 (English). Unit-test both.
4. `kb/ocr.py`: RapidOCR on image-only pages and on pages whose text layer is empty; returns lines with boxes and
   confidence; cache by page image hash in `knowledge/build/ocr_cache/`.
5. `kb/vision.py` (stub today, used Day 5): Gemini vision transcription with P2; reconciliation function.
6. `kb/build.py` writes `knowledge/build/pages.parquet` and `report.md` (pages per method, OCR conf histogram,
   excluded pages with reason).
7. CLI: `python -m claimguard.kb build [--no-ocr] [--doc ID]`.
## Antigravity
Audit screen on mocks: input tabs (Paste, Upload, Pack image, Sample), context fields, Run button, ProgressSteps
component (animated from mock SSE), result layout skeleton with stat row.
## Tests
- test_script_detect (fixtures from FSSAI p.5 legacy text and p.21 English text).
- test_ocr_adapter on a small fixture image with known text.
- test_build_accounts_every_page.
## Done when
Build report shows all 141 pages accounted for: CCPA-GW 6 OCR pages, ASCI 5 image pages OCR'd, ASCI-INF pages
4/9/18 OCR'd, FSSAI 18 legacy pages excluded. Paste a screenshot of report.md into PROGRESS.md.
