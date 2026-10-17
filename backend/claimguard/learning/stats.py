"""Reliability from reviewer feedback: accept / dismiss rate per clause and per claim type (Beta(1,1) prior)."""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import select

from ..db import CitationRow, ClaimRow, Feedback, FlagRow, session

MIN_OBS = 10


def counts(db_url: str | None = None) -> dict:
    """{'clause': {id: [accept, dismiss]}, 'type': {claim_type: [accept, dismiss]}, 'pairs': [(conf, accepted)]}"""
    out = {"clause": defaultdict(lambda: [0, 0]), "type": defaultdict(lambda: [0, 0]), "pairs": []}
    with session(db_url) as s:
        latest = {r.flag_id: r for r in s.exec(select(Feedback).order_by(Feedback.id)).all()}
        for fid, fb in latest.items():
            if fb.action not in ("accept", "dismiss", "set_risk"):
                continue
            flag = s.get(FlagRow, fid)
            if not flag:
                continue
            ok = fb.action == "accept" or (fb.action == "set_risk" and fb.to_risk not in (None, "low"))
            claim = s.get(ClaimRow, flag.claim_id)
            out["type"][claim.claim_type if claim else "?"][0 if ok else 1] += 1
            for c in s.exec(select(CitationRow).where(CitationRow.flag_id == fid)).all():
                out["clause"][c.clause_id][0 if ok else 1] += 1
            if flag.confidence is not None:
                out["pairs"].append((flag.confidence, int(ok)))
    return out


def reliability(acc: int, dis: int) -> float:
    return (acc + 1) / (acc + dis + 2)


def clause_stats(clause_id: str, db_url: str | None = None) -> dict:
    a, d = counts(db_url)["clause"].get(clause_id, [0, 0])
    return {"used_in": a + d, "accept_rate": round(a / (a + d), 3) if a + d else None}


def reweight(clause_id: str, c: dict) -> float:
    """Multiplier for rerank ordering; neutral until MIN_OBS reviewer decisions exist for the clause."""
    a, d = c["clause"].get(clause_id, [0, 0])
    return 1.0 if a + d < MIN_OBS else 0.5 + reliability(a, d)
