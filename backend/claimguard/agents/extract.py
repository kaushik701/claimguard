"""LLM claim extractor (P3): multi-claim, shortest exact substring; anything not found verbatim is dropped."""
from __future__ import annotations

from ..llm.prompts import render
from ..llm.schemas import CLAIM_TYPES, ExtractOut
from .models import Claim
from .rule_extract import footnotes, qualifier_status, sentence_at


def extract_llm(llm, text: str, surface: str, category: str, paid: bool, few_shot: str = "") -> list[Claim]:
    prompt = render("claim_extractor", few_shot_examples=few_shot or "(none)", surface=surface, category=category,
                    paid=str(paid).lower(), text=text)
    out = llm.json("claim_extractor", prompt, ExtractOut, step="extract")
    notes = footnotes(text)
    claims, used = [], set()
    for x in out.claims:
        if not x.text.strip():
            continue
        pos = text.find(x.text)
        while pos >= 0 and (pos, x.text) in used:          # same phrase twice: take the next occurrence
            pos = text.find(x.text, pos + 1)
        if pos < 0:
            continue                                       # paraphrased / hallucinated span: dropped
        used.add((pos, x.text))
        q, sd = qualifier_status(x.text, notes)
        if not q:
            q, sd = qualifier_status(sentence_at(text, pos), notes)
        ctype = x.claim_type if x.claim_type in CLAIM_TYPES else "puffery"
        claims.append(Claim(text=x.text, start=pos, end=pos + len(x.text), claim_type=ctype, source="llm",
                            qualifier=q or (x.has_qualifier and bool(x.footnote_text)), source_date=sd,
                            footnote_text=x.footnote_text))
    return claims
