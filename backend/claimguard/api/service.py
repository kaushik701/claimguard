"""Persistence + serialisation between the agent chain, SQLite and the API contract."""
from __future__ import annotations

import time

from sqlmodel import select

from ..agents.models import AuditOutput
from ..agents.normalise import boxes_for
from ..config import settings
from ..db import Audit, CitationRow, ClaimRow, Feedback, FlagRow, Run, session
from ..kb.clauses import clauses_by_id


def save_output(db_url, audit_id: int, out: AuditOutput, llm=None, started: float | None = None) -> None:
    with session(db_url) as s:
        a = s.get(Audit, audit_id)
        claim_ids: dict[tuple[int, str], int] = {}
        for c in out.claims:
            row = ClaimRow(audit_id=audit_id, text=c.text, start=c.start, end=c.end, claim_type=c.claim_type,
                           alt_types=c.alt_types, source=c.source, qualifier=c.qualifier, source_date=c.source_date)
            s.add(row)
            s.flush()
            claim_ids[(c.start, c.text)] = row.id
        for f in out.flags:
            fr = FlagRow(audit_id=audit_id, claim_id=claim_ids.get((f.claim.start, f.claim.text), 0), risk=f.risk,
                         reason=f.reason, rewrite=f.rewrite, confidence=f.confidence, verifier_note=f.verifier_note)
            s.add(fr)
            s.flush()
            for i, c in enumerate(f.citations):
                s.add(CitationRow(flag_id=fr.id, clause_id=c.clause_id, quote=c.quote, rank=i))
        tin = tout = 0
        if llm is not None:
            for call in llm.calls:
                s.add(Run(audit_id=audit_id, step=call.get("prompt", ""), model=call.get("model", ""),
                          prompt_hash=call.get("prompt_hash", ""), output_json={"raw": call.get("output", "")[:4000]},
                          ms=call.get("ms", 0), tokens_in=call.get("tokens_in", 0), tokens_out=call.get("tokens_out", 0)))
                tin += call.get("tokens_in", 0)
                tout += call.get("tokens_out", 0)
        p = settings()["llm"]
        a.tokens_in, a.tokens_out = tin, tout
        a.cost_usd = round((tin * p.get("price_in", 0) + tout * p.get("price_out", 0)) / 1e6, 6)
        a.result = {"not_covered": [c.model_dump() for c in out.not_covered],
                    "low_risk": [c.model_dump() for c in out.low_risk],
                    "dropped": [d.model_dump() for d in out.dropped], "fallback_reason": out.fallback_reason}
        a.fallback_used = out.fallback_used
        a.steps = out.steps
        a.status = "done"
        a.latency_ms = int((time.time() - started) * 1000) if started else sum(x["ms"] for x in out.steps[-1:])
        s.add(a)
        s.commit()


def citation_dict(row: CitationRow, store: dict) -> dict:
    cl = store.get(row.clause_id, {})
    return {"clause_id": row.clause_id, "doc_id": cl.get("doc_id", ""), "doc_title": cl.get("doc_title", ""),
            "section_path": cl.get("section_path", ""), "number": cl.get("number"), "page": cl.get("page_start", 0),
            "quote": row.quote, "source": cl.get("source", "text"), "ocr_conf": cl.get("ocr_conf")}


def flag_dict(s, f: FlagRow, store: dict, boxes: list | None = None) -> dict:
    c = s.get(ClaimRow, f.claim_id)
    cits = s.exec(select(CitationRow).where(CitationRow.flag_id == f.id).order_by(CitationRow.rank)).all()
    claim = {"id": str(c.id), "text": c.text, "start": c.start, "end": c.end, "claim_type": c.claim_type,
             "source": c.source} if c else {}
    a = s.get(Audit, f.audit_id)
    return {"id": f.id, "audit_id": f.audit_id, "claim": claim, "risk": f.risk, "reason": f.reason, "rewrite": f.rewrite,
            "confidence": f.confidence, "verifier_note": f.verifier_note,
            "citations": [citation_dict(x, store) for x in cits], "status": f.status,
            "reviewer_risk": f.reviewer_risk, "reviewer_note": f.reviewer_note,
            "brand": a.brand if a else "", "surface": a.surface if a else "", "category": a.category if a else "",
            "boxes": boxes_for(c.start, c.end, boxes) if (boxes and c) else []}


def audit_dict(db_url, audit_id: int) -> dict | None:
    store = clauses_by_id()
    with session(db_url) as s:
        a = s.get(Audit, audit_id)
        if not a:
            return None
        flags = s.exec(select(FlagRow).where(FlagRow.audit_id == audit_id)).all()
        claims = s.exec(select(ClaimRow).where(ClaimRow.audit_id == audit_id)).all()
        fl = [flag_dict(s, f, store, a.ocr_boxes) for f in flags]
        order = {"high": 0, "medium": 1, "low": 2}
        fl.sort(key=lambda x: (order.get(x["reviewer_risk"] or x["risk"], 3), x["claim"].get("start", 0)))
        r = a.result or {}
        return {
            "id": a.id, "created_at": a.created_at.isoformat(), "status": a.status, "error": a.error,
            "input_type": a.input_type, "surface": a.surface, "category": a.category, "brand": a.brand,
            "paid": a.paid, "text": a.text, "image_url": f"/api/audits/{a.id}/image" if a.image_path else None,
            "ocr_boxes": a.ocr_boxes, "mode": a.mode, "steps": a.steps,
            "claims": [{"id": str(c.id), "text": c.text, "start": c.start, "end": c.end, "claim_type": c.claim_type,
                        "source": c.source} for c in claims],
            "flags": fl, "not_covered": r.get("not_covered", []), "low_risk": r.get("low_risk", []),
            "dropped": r.get("dropped", []), "fallback_used": a.fallback_used,
            "fallback_reason": r.get("fallback_reason"),
            "stats": {"claims": len(claims), "high": sum(f["risk"] == "high" for f in fl),
                      "medium": sum(f["risk"] == "medium" for f in fl),
                      "not_covered": len(r.get("not_covered", [])), "dropped": len(r.get("dropped", []))},
            "latency_ms": a.latency_ms, "tokens_in": a.tokens_in, "tokens_out": a.tokens_out, "cost_usd": a.cost_usd,
        }


def apply_feedback(db_url, flag_id: int, action: str, risk=None, reason_code=None, note=None, reviewer=None) -> dict:
    with session(db_url) as s:
        f = s.get(FlagRow, flag_id)
        if not f:
            return {}
        before = f.reviewer_risk or f.risk
        status = {"accept": "accepted", "dismiss": "dismissed", "escalate": "escalated", "set_risk": f.status}[action]
        f.status = status if status != "open" or action != "set_risk" else f.status
        if action == "set_risk":
            f.reviewer_risk = risk
            if f.status == "open":
                f.status = "accepted"
        if note is not None:
            f.reviewer_note = note
        s.add(Feedback(flag_id=flag_id, action=action, from_risk=before,
                       to_risk=risk if action == "set_risk" else ("low" if action == "dismiss" else before),
                       reason_code=reason_code, note=note, reviewer=reviewer))
        s.add(f)
        s.commit()
        return flag_dict(s, f, clauses_by_id())
