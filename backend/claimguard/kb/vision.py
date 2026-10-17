"""Vision second reader (prompt P2) and OCR/vision reconciliation.

Model from settings [llm] vision_model (default qwen/qwen3.8-27b on Groq; a gemini-* name uses Gemini). Used for
infographic pages and pack images when that provider's key is set; otherwise OCR only (caller shows a note).
Reconciliation keeps the OCR text and marks OCR lines the vision model does not confirm."""
from __future__ import annotations

import base64
import json
import os
import re

from ..config import KEY_ENV, settings
from ..llm.client import BASE_URL, provider_for
from ..llm.prompts import template
from ..llm.schemas import VisionBlock, VisionOut


def _model() -> tuple[str, str]:
    m = settings()["llm"].get("vision_model", "qwen/qwen3.8-27b")
    return provider_for(m, "groq"), m


def available() -> bool:
    return bool(os.getenv(KEY_ENV[_model()[0]]))


def parse(raw: str) -> VisionOut:
    """Accept P2's {"blocks":[{"text","position"}]} and common variants ({"text_content", "bbox_2d"} lists)."""
    s = raw.strip()
    m = re.search(r"[\[{].*[\]}]", s, re.S)
    data = json.loads(m.group(0)) if m else {}
    items = data.get("blocks", data) if isinstance(data, dict) else data
    if isinstance(items, dict):
        items = next((v for v in items.values() if isinstance(v, list)), [])
    blocks = []
    for it in items or []:
        if isinstance(it, dict):
            t = it.get("text") or it.get("text_content") or ""
            if str(t).strip():
                blocks.append(VisionBlock(text=str(t), position=str(it.get("position") or it.get("bbox_2d") or "")))
        elif isinstance(it, str) and it.strip():
            blocks.append(VisionBlock(text=it))
    return VisionOut(blocks=blocks, notes=data.get("notes") if isinstance(data, dict) else None)


def read_image(png: bytes) -> VisionOut:
    from openai import OpenAI
    provider, model = _model()
    client = OpenAI(base_url=BASE_URL[provider], api_key=os.environ[KEY_ENV[provider]], timeout=60, max_retries=1)
    mime = "image/jpeg" if png[:3] == b"\xff\xd8\xff" else "image/png"
    resp = client.chat.completions.create(
        model=model, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": [
            {"type": "text", "text": template("vision_reader")},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(png).decode()}"}}]}])
    return parse(resp.choices[0].message.content or "{}")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9%]+", " ", s.lower()).strip()


def reconcile(ocr_lines: list[dict], vision: VisionOut | None) -> list[dict]:
    """Each OCR line gets `vision_agrees` (True/False/None when no vision reading)."""
    if vision is None:
        return [{**ln, "vision_agrees": None} for ln in ocr_lines]
    vtext = " " + _norm(" ".join(b.text for b in vision.blocks)) + " "
    return [{**ln, "vision_agrees": bool(_norm(ln["text"])) and f" {_norm(ln['text'])} " in vtext} for ln in ocr_lines]
