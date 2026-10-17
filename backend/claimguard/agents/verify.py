"""Citation guard (code, never bypassed): NO CITATION, NO FLAG.

A flag survives only if
  1. its evidence span (or claim text) appears verbatim in the input (whitespace/quote normalised),
  2. at least one citation names a clause that was RETRIEVED for this claim, and
  3. that citation's quote is >= min_quote_chars and appears verbatim in the clause text.
Citations failing 2-3 are removed; a flag with none left is dropped (reason recorded).
Low-OCR-confidence clauses (< low_ocr_conf) cannot alone produce a HIGH flag: lowered to MEDIUM unless the rule
judge independently rates the claim high."""
from __future__ import annotations

from ..config import settings
from ..kb.segment import norm
from .models import Dropped, Flag


def guard(flag: Flag, text: str, retrieved: list[dict], rule_risk: str | None = None) -> tuple[Flag | None, Dropped | None]:
    th = settings()["thresholds"]
    span = flag.evidence_span or flag.claim.text
    if norm(span) not in norm(text) and norm(flag.claim.text) not in norm(text):
        return None, Dropped(claim=flag.claim.text, reason="evidence span not found in the input", stage="citation_guard")
    by_id = {r["clause_id"]: r for r in retrieved}
    good = []
    for c in flag.citations:
        cl = by_id.get(c.clause_id)
        q = norm(c.quote)
        if cl and len(q) >= th["min_quote_chars"] and q in norm(cl["text"]):
            good.append(c)
    if not good:
        return None, Dropped(claim=flag.claim.text, stage="citation_guard",
                             reason="no citation quotes a retrieved clause verbatim (>= "
                                    f"{th['min_quote_chars']} characters)")
    flag.citations = good
    if flag.risk == "high" and all((c.ocr_conf is not None and c.ocr_conf < th["low_ocr_conf"]) for c in good) \
            and rule_risk != "high":
        flag.risk = "medium"
        flag.verifier_note = (flag.verifier_note or "") + " Lowered: only low-OCR-confidence clauses support it."
    return flag, None
