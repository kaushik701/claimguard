"""Normaliser: text | html | pdf | image -> plain text (+ OCR boxes for images, with character offsets)."""
from __future__ import annotations

import re

from ..config import settings

ALLOWED = {"html": (".html", ".htm"), "pdf": (".pdf",), "image": (".png", ".jpg", ".jpeg")}
MAGIC = {"pdf": [b"%PDF"], "image": [b"\x89PNG", b"\xff\xd8\xff"]}


class InputError(ValueError):
    pass


def check_upload(kind: str, name: str, data: bytes) -> None:
    mb = settings()["app"]["max_upload_mb"]
    if len(data) > mb * 1024 * 1024:
        raise InputError(f"File is larger than {mb} MB.")
    if not name.lower().endswith(ALLOWED[kind]):
        raise InputError(f"Expected a {', '.join(ALLOWED[kind])} file for '{kind}'.")
    if kind in MAGIC and not any(data.startswith(m) for m in MAGIC[kind]):
        raise InputError(f"The file does not look like a real {kind.upper()}.")


def from_html(data: bytes) -> str:
    import trafilatura
    txt = trafilatura.extract(data.decode("utf-8", "ignore"), include_comments=False, include_tables=True) or ""
    if not txt.strip():  # very small pages: strip tags
        txt = re.sub(r"<[^>]+>", " ", data.decode("utf-8", "ignore"))
    return re.sub(r"[ \t]+", " ", txt).strip()


def from_pdf(data: bytes) -> str:
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    parts = []
    for page in doc:
        t = page.get_text().strip()
        if len(t) < 20:
            from ..kb.ocr import OCR_DPI, ocr_png
            t = "\n".join(x["text"] for x in ocr_png(page.get_pixmap(dpi=OCR_DPI).tobytes("png"), OCR_DPI / 72))
        parts.append(t)
    return "\n".join(parts).strip()


def from_image(data: bytes, use_vision: bool = True) -> tuple[str, list[dict], str | None]:
    """OCR (+ vision reconcile when a Gemini key exists) -> (text, boxes with start/end offsets, note)."""
    from ..kb import vision
    from ..kb.ocr import ocr_png
    lines = ocr_png(data)
    note = None
    v = None
    if use_vision and vision.available():
        try:
            v = vision.read_image(data)
        except Exception as e:  # vision optional
            note = f"vision reader unavailable ({str(e)[:80]}); OCR only"
    elif use_vision:
        note = "OCR only (no GEMINI_API_KEY for the vision reader)"
    lines = vision.reconcile(lines, v)
    text, boxes = "", []
    for ln in lines:
        start = len(text)
        text += ln["text"] + "\n"
        boxes.append({**ln, "start": start, "end": start + len(ln["text"])})
    return text.strip(), boxes, note


def boxes_for(start: int, end: int, boxes: list[dict]) -> list[list[float]]:
    return [b["box"] for b in boxes if b["start"] < end and b["end"] > start]
