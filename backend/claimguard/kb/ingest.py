"""Per-page ingestion: text layer with font info, page images, script per block, OCR where the text layer is empty.

Page record: doc_id, page (1-based), method (text|ocr|excluded), script (en|mixed|hi_legacy|image_only),
text (English text kept), blocks (json: text, size, bold, bbox, source), ocr_conf, dropped_blocks, reason."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf
import yaml

from ..config import ROOT, path
from . import ocr as ocr_mod
from .script_detect import classify, legacy_line, page_script

UI_DPI = 150
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_LETTERS = re.compile(r"[A-Za-z]")


def sources() -> list[dict]:
    return yaml.safe_load((ROOT / "knowledge" / "sources.yaml").read_text(encoding="utf-8"))


def clean(s: str) -> str:
    return _CONTROL.sub("", s)


def text_blocks(page) -> list[dict]:
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        lines, sizes, bold = [], [], []
        for ln in b["lines"]:
            spans = [s for s in ln["spans"] if s["text"].strip()]
            if not spans:
                continue
            line = clean("".join(s["text"] for s in ln["spans"])).rstrip()
            if legacy_line(line):
                continue
            lines.append(line)
            sizes += [s["size"] for s in spans]
            bold += [bool(s["flags"] & 16) or "Bold" in s["font"] for s in spans]
        txt = "\n".join(lines).strip()
        if txt:
            out.append({"text": txt, "size": round(max(sizes), 1), "bold": all(bold),
                        "bbox": [round(v, 1) for v in b["bbox"]], "source": "text"})
    return out


def ingest_doc(src: dict, ocr: bool = True, images: bool = True) -> list[dict]:
    pdf = ROOT / "knowledge" / "pdfs" / src["file"]
    doc = pymupdf.open(pdf)
    img_dir = path("build") / "page_images" / src["id"]
    cache = path("build") / "ocr_cache"
    pages = []
    for i, page in enumerate(doc, 1):
        if images:
            img_dir.mkdir(parents=True, exist_ok=True)
            f = img_dir / f"{i}.png"
            if not f.exists():
                page.get_pixmap(dpi=UI_DPI).save(f)
        blocks = text_blocks(page)
        for b in blocks:
            b["script"] = classify(b["text"])
        kept = [b for b in blocks if b["script"] == "en"]
        dropped = len(blocks) - len(kept)
        script = page_script([b["script"] for b in blocks])
        text = "\n".join(b["text"] for b in kept)
        rec = {"doc_id": src["id"], "page": i, "script": script, "ocr_conf": None, "dropped_blocks": dropped,
               "reason": "", "width": page.rect.width, "height": page.rect.height}
        if len(_LETTERS.findall(text)) >= 50:
            rec.update(method="text", text=text, blocks=kept)
        elif dropped:  # Hindi blocks and too little English: never OCR (OCR reads the legacy font as gibberish)
            rec.update(method="excluded", text="", blocks=[], reason="Hindi in a legacy font (cannot be cited)")
        elif ocr:
            lines = ocr_mod.ocr_page(page, cache)
            otext = "\n".join(ln["text"] for ln in lines)
            if classify(otext) != "en":
                rec.update(method="excluded", text="", blocks=[], reason="OCR text is not English")
            elif len(_LETTERS.findall(otext)) >= 20:
                rec.update(method="ocr", text=otext, ocr_conf=ocr_mod.mean_conf(lines),
                           blocks=[{"text": ln["text"], "size": 0, "bold": False, "bbox": ln["box"], "source": "ocr",
                                    "conf": ln["conf"], "script": "en"} for ln in lines])
                if script != "mixed":
                    rec["script"] = "image_only" if not blocks else script
            else:
                rec.update(method="excluded", text=text, blocks=kept,
                           reason="no readable text (divider or picture page; OCR found < 20 letters)")
        else:
            rec.update(method="excluded", text=text, blocks=kept, reason="OCR skipped (--no-ocr)")
        rec["blocks"] = json.dumps(rec["blocks"], ensure_ascii=False)
        pages.append(rec)
    return pages


def load_pages() -> list[dict]:
    import pandas as pd
    df = pd.read_parquet(path("build") / "pages.parquet")
    recs = df.to_dict("records")
    for r in recs:
        r["blocks"] = json.loads(r["blocks"])
    return recs


def page_image(doc_id: str, page: int) -> Path:
    return path("build") / "page_images" / doc_id / f"{page}.png"
