"""Verifier agent (P7, run on a different model than the judge): does each cited clause, read plainly, support
the flag? Only LOWERS risk: high -> medium, medium -> dropped to low risk. confidence = judge x verifier."""
from __future__ import annotations

from ..llm.prompts import template
from ..llm.schemas import VerifyOut
from .models import Dropped, Flag


def verify_flags(llm, text: str, flags: list[Flag], clauses: dict[str, dict]):
    if not flags:
        return []
    blocks = []
    for i, f in enumerate(flags):
        cites = "\n".join(f"    [{c.clause_id}] {clauses.get(c.clause_id, {}).get('text', c.quote)}" for c in f.citations)
        blocks.append(f"FLAG {i}: risk={f.risk}; type={f.claim.claim_type}\n  claim: {f.claim.text}\n"
                      f"  reason: {f.reason}\n  cited clauses (full text):\n{cites}")
    from ..llm.prompts import neutralise
    prompt = template("verifier") + "\n\n<<<INPUT\n" + neutralise(text) + "\nINPUT>>>\n\n" + "\n\n".join(blocks)
    return llm.json("verifier", prompt, VerifyOut, step="verifier").verdicts


def apply(flags: list[Flag], verdicts) -> tuple[list[Flag], list, list[Dropped]]:
    """-> (kept flags, claims moved to low risk, dropped records)."""
    by = {v.flag_index: v for v in verdicts if 0 <= v.flag_index < len(flags)}
    kept, low, dropped = [], [], []
    for i, f in enumerate(flags):
        v = by.get(i)
        if v is None:
            kept.append(f)
            continue
        f.confidence = round((f.confidence if f.confidence is not None else 1.0) * v.confidence, 3)
        if v.supports:
            kept.append(f)
            continue
        note = (v.issue or "The cited clause does not clearly support this flag.").strip()
        if f.risk == "high":
            f.risk, f.verifier_note = "medium", note
            kept.append(f)
        else:
            low.append(f.claim)
            dropped.append(Dropped(claim=f.claim.text, reason=f"verifier: {note}", stage="verifier"))
    return kept, low, dropped
