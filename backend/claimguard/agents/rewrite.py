"""Rewriter (P8) + code guard: a rewrite may not introduce numbers, years or % that are not in the input
(outside <placeholders>); otherwise the judge's wording (or a placeholder template) is kept."""
from __future__ import annotations

import re

from ..llm.prompts import neutralise, template
from ..llm.schemas import RewriteOut
from .models import Flag

_NUM = re.compile(r"\d+(?:\.\d+)?")
_PH = re.compile(r"<[^<>]{1,60}>")

TEMPLATES = {
    "efficacy": "{claim}* — *In <test type> vs <baseline>, <conditions>. Source: <study>, <year>.",
    "comparative": "<Attribute> vs <named baseline>* — *<test method>, <lab>, <year>.",
    "leadership": "{claim} (Source: <independent data provider>, <metric>, <period>).",
    "awards_rankings": "{claim} (Awarded by <body>, <year>, <basis>).",
    "time_bound": "{claim}* — *In a <study type> on <N> participants, <year>. Results may vary.",
    "appearance": "<Measured outcome>* — *<study type>, n=<N>, <duration>, <year>. Results may vary.",
    "scientific": "{claim}* — *<Independent lab/clinic>, <study type>, <year>.",
    "environmental": "<Specific part, e.g. bottle> made with <X>% recycled <material>; details: <link>.",
    "natural_purity": "With <ingredient> from <source>.",
    "nutrition_health": "Contains <nutrient>, which contributes to <normal function> (as permitted).",
    "disclosure": "#ad | {claim}",
}


def safe(rewrite: str | None, text: str) -> bool:
    if not rewrite:
        return False
    outside = _PH.sub("", rewrite)
    return all(n in text for n in _NUM.findall(outside))


def fallback(f: Flag) -> str | None:
    t = TEMPLATES.get(f.claim.claim_type)
    return t.format(claim=f.claim.text.rstrip(".*")) if t else None


def rewrite(llm, text: str, flags: list[Flag]) -> None:
    if llm is not None and flags:
        block = "\n".join(f"FLAG {i}: claim: {f.claim.text} | reason: {f.reason} | draft: {f.rewrite or ''}"
                          for i, f in enumerate(flags))
        prompt = template("rewriter") + "\n\n<<<INPUT\n" + neutralise(text) + "\nINPUT>>>\n\n" + block
        try:
            for r in llm.json("rewriter", prompt, RewriteOut, step="rewrite").rewrites:
                if 0 <= r.flag_index < len(flags) and safe(r.text, text):
                    flags[r.flag_index].rewrite = r.text
        except Exception:
            pass
    for f in flags:
        if not safe(f.rewrite, text):
            f.rewrite = fallback(f)
