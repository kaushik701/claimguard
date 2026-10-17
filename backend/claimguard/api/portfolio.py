"""Portfolio: brand x claim-type heatmap, flags by regulator and surface, recurring phrasings, open vs resolved."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from sqlmodel import select

from ..db import Audit, CitationRow, ClaimRow, FlagRow, session
from ..kb.clauses import clauses_by_id

_TOK = re.compile(r"[a-z0-9%]+")


def _sim(a: str, b: str) -> float:
    x, y = set(_TOK.findall(a.lower())), set(_TOK.findall(b.lower()))
    return len(x & y) / len(x | y) if x and y else 0.0


def clusters(texts: list[str], threshold: float = 0.4) -> list[dict]:
    """Greedy grouping of similar risky phrasings (token overlap)."""
    groups: list[list[str]] = []
    for t in texts:
        for g in groups:
            if _sim(t, g[0]) >= threshold:
                g.append(t)
                break
        else:
            groups.append([t])
    return sorted(({"phrase": g[0], "count": len(g), "examples": g[:5]} for g in groups if len(g) > 1),
                  key=lambda x: -x["count"])[:10]


def build(db_url=None) -> dict:
    store = clauses_by_id()
    heat, reg, surf, trend = defaultdict(Counter), Counter(), Counter(), defaultdict(Counter)
    texts = []
    with session(db_url) as s:
        for f in s.exec(select(FlagRow)).all():
            a, c = s.get(Audit, f.audit_id), s.get(ClaimRow, f.claim_id)
            if not a or not c:
                continue
            heat[a.brand or "(no brand)"][c.claim_type] += 1
            surf[(a.surface, f.risk)] += 1
            for ct in s.exec(select(CitationRow).where(CitationRow.flag_id == f.id)).all():
                reg[store.get(ct.clause_id, {}).get("regulator", "?")] += 1
            day = a.created_at.strftime("%Y-%m-%d")
            trend[day]["open" if f.status in ("open", "escalated") else "resolved"] += 1
            texts.append(c.text)
    types = sorted({t for row in heat.values() for t in row})
    return {"heatmap": {"types": types, "rows": [{"brand": b, "counts": dict(r)} for b, r in sorted(heat.items())]},
            "by_regulator": [{"regulator": k, "count": v} for k, v in reg.most_common()],
            "by_surface": [{"surface": k, "risk": r, "count": v} for (k, r), v in sorted(surf.items())],
            "phrasings": clusters(texts), "trend": [{"day": d, **dict(v)} for d, v in sorted(trend.items())]}
