"""OCR adapter (RapidOCR, CPU). Returns lines with boxes (PDF points) and confidence; cached by image hash."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

OCR_DPI = 200
_ENGINE = None


def engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr import RapidOCR
        _ENGINE = RapidOCR()
    return _ENGINE


def ocr_png(png: bytes, scale: float = 1.0) -> list[dict]:
    """Lines in reading order: {text, conf, box:[x0,y0,x1,y1]} with box divided by `scale`."""
    r = engine()(png)
    out = []
    for txt, conf, box in zip(r.txts or [], r.scores or [], r.boxes if r.boxes is not None else []):
        xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
        out.append({"text": txt, "conf": round(float(conf), 3),
                    "box": [round(min(xs) / scale, 1), round(min(ys) / scale, 1),
                            round(max(xs) / scale, 1), round(max(ys) / scale, 1)]})
    return out


def ocr_page(page, cache_dir: Path) -> list[dict]:
    pix = page.get_pixmap(dpi=OCR_DPI)
    png = pix.tobytes("png")
    key = hashlib.sha256(png).hexdigest()[:20]
    f = cache_dir / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    lines = ocr_png(png, scale=OCR_DPI / 72)
    cache_dir.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    return lines


def mean_conf(lines: list[dict]) -> float | None:
    return round(sum(x["conf"] for x in lines) / len(lines), 3) if lines else None
