"""Vision second reader (Gemini, prompt P2) and OCR/vision reconciliation.

Used for infographic pages and pack images when GEMINI_API_KEY is set; otherwise OCR only (caller shows a
banner). Reconciliation keeps the OCR text and marks OCR lines the vision model does not confirm."""
from __future__ import annotations

import base64
import os
import re

from ..llm.prompts import template
from ..llm.schemas import VisionOut


def available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def read_image(png: bytes, model: str = "gemini-2.5-flash") -> VisionOut:
    from openai import OpenAI
    client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    api_key=os.environ["GEMINI_API_KEY"], timeout=60, max_retries=1)
    b64 = base64.b64encode(png).decode()
    resp = client.chat.completions.create(
        model=model, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": [
            {"type": "text", "text": template("vision_reader")},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}])
    return VisionOut.model_validate_json(resp.choices[0].message.content or "{}")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9%]+", " ", s.lower()).strip()


def reconcile(ocr_lines: list[dict], vision: VisionOut | None) -> list[dict]:
    """Each OCR line gets `vision_agrees` (True/False/None when no vision reading)."""
    if vision is None:
        return [{**ln, "vision_agrees": None} for ln in ocr_lines]
    vtext = " " + _norm(" ".join(b.text for b in vision.blocks)) + " "
    out = []
    for ln in ocr_lines:
        t = _norm(ln["text"])
        out.append({**ln, "vision_agrees": bool(t) and f" {t} " in vtext})
    return out
