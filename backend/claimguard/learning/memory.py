"""Few-shot memory from reviewer decisions. Accepted / risk-changed flags become positive examples; dismissed
flags (with reason code) become hard negatives. The top-k most similar past decisions are inserted into the
extractor/judge prompts. Anything whose text matches a held-out item is never used (AGENTS.md rule 3)."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from sqlmodel import select

from ..config import ROOT
from ..db import ClaimRow, Feedback, FlagRow, session
from ..kb.segment import norm

_TOK = re.compile(r"[a-z0-9%]+")


@lru_cache(maxsize=1)
def holdout_texts() -> frozenset[str]:
    out = set()
    for f in (ROOT / "data" / "gold").glob("holdout*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.add(norm(json.loads(line)["text"]))
    return frozenset(out)


def is_holdout(text: str) -> bool:
    t = norm(text)
    return any(t == h or (len(h) > 15 and (h in t or t in h)) for h in holdout_texts())


def decisions(db_url: str | None = None) -> list[dict]:
    """Latest decision per flag: {claim, claim_type, clause_ids, final_risk, action, reason_code, note}."""
    with session(db_url) as s:
        rows = s.exec(select(Feedback).order_by(Feedback.id)).all()
        latest = {r.flag_id: r for r in rows}
        out = []
        for fid, fb in latest.items():
            flag = s.get(FlagRow, fid)
            claim = s.get(ClaimRow, flag.claim_id) if flag else None
            if not claim or is_holdout(claim.text):
                continue
            final = fb.to_risk or (flag.risk if fb.action == "accept" else ("low" if fb.action == "dismiss" else flag.risk))
            out.append({"claim": claim.text, "claim_type": claim.claim_type, "final_risk": final, "action": fb.action,
                        "model_risk": flag.risk, "reason_code": fb.reason_code, "note": fb.note or ""})
        return out


def _sim(a: str, b: str) -> float:
    x, y = set(_TOK.findall(a.lower())), set(_TOK.findall(b.lower()))
    return len(x & y) / len(x | y) if x and y else 0.0


def similar(claim: str, k: int = 3, db_url: str | None = None, min_sim: float = 0.2) -> list[dict]:
    ds = [d for d in decisions(db_url) if _sim(claim, d["claim"]) >= min_sim]
    return sorted(ds, key=lambda d: -_sim(claim, d["claim"]))[:k]


def examples_text(claims: list[str], k: int = 3, db_url: str | None = None) -> str:
    seen, lines = set(), []
    for c in claims:
        for d in similar(c, k, db_url):
            key = (d["claim"], d["action"])
            if key in seen:
                continue
            seen.add(key)
            if d["action"] == "dismiss":
                lines.append(f'- "{d["claim"]}" ({d["claim_type"]}): previously judged NOT risky by a reviewer '
                             f'because {d["reason_code"] or "other"}{": " + d["note"] if d["note"] else ""}.')
            else:
                lines.append(f'- "{d["claim"]}" ({d["claim_type"]}): reviewer confirmed risk {d["final_risk"].upper()}'
                             f'{": " + d["note"] if d["note"] else ""}.')
    return "\n".join(lines[: k * 2])
