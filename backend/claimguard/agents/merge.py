"""Merge LLM and rule claims: same claim when spans overlap by >= 50% of the shorter span. LLM span and type
win; the rule type goes to alt_types; source = both. Rule-only claims are kept (safety net)."""
from __future__ import annotations

from .models import Claim


def overlap(a: Claim, b: Claim) -> bool:
    s, e = max(a.start, b.start), min(a.end, b.end)
    return e - s >= 0.5 * min(a.end - a.start, b.end - b.start)


def merge(llm: list[Claim], rules: list[Claim]) -> list[Claim]:
    out, matched = [], set()
    for lc in llm:
        c = lc.model_copy(deep=True)
        for i, rc in enumerate(rules):
            if overlap(c, rc):
                matched.add(i)
                c.source = "both"
                if rc.claim_type != c.claim_type and rc.claim_type not in c.alt_types:
                    c.alt_types.append(rc.claim_type)
                c.qualifier = c.qualifier or rc.qualifier
                c.source_date = c.source_date or rc.source_date
        out.append(c)
    out += [rc for i, rc in enumerate(rules) if i not in matched]
    out.sort(key=lambda c: c.start)
    for i, c in enumerate(out, 1):
        c.id = f"c{i}"
    return out
