# Day 5: Pack images, uploads, pre-flight

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. Image input: OCR (boxes + conf) + vision (P2) → reconcile → text with box map; claims map back to boxes.
2. HTML upload (trafilatura/readability text), PDF upload (text layer, OCR fallback). 2 MB cap.
3. `POST /preflight` (synchronous, same pipeline, verdict rule: any high → revise; medium only → check; else
   clear with caveat).
4. Two fictional pack images in `data/samples/packs/` (make them with a simple HTML-to-PNG render, fictional
   brand).
## Antigravity
Pack-image input with preview and OCR boxes drawn (colour by risk once results arrive); Pre-flight screen with
verdict banner and "Copy all fixes".
## Tests
test_image_pipeline_maps_boxes, test_html_upload_text, test_preflight_verdicts.
## Done when
A pack photo audit shows claims highlighted on the image.
