"""Judge: LLM (P6, one call per input) with the written rubric; deterministic rule judge as fallback/baseline."""
from __future__ import annotations

import re

from ..llm.prompts import render
from ..llm.schemas import JudgeOut
from .models import Citation, Claim, Flag

# ---------------------------------------------------------------- rule judge (baseline, mirrors P6 policy)
_ABS = re.compile(r"\b100\s?%|\ball\s+germs\b|\bcomplete\s+protection\b|\btotal\s+protection\b", re.I)
_NUM = re.compile(r"\d")
_SPF = re.compile(r"^\W*(spf\s?\d+|pa\+{1,4}|broad[- ]spectrum|protection|\W|\s)+\W*$", re.I)
_DENIG = re.compile(r"\b(lie|lies|lying|fake|cheat|useless|harmful|dangerous)\b", re.I)
_OWN = re.compile(r"\b(previous|old|our\s+earlier|earlier)\s+(formula|version|pack)\b", re.I)
_SOCIAL = re.compile(r"\b(job|marriage|husband|wife|confidence|success|promotion|interview)\b", re.I)
_FAIR = re.compile(r"\bfair(er|ness)\b|\bwhiten|\blighter\b|\blighten", re.I)
_ENV_ABS = re.compile(r"\beco[- ]?friendly|environment(ally)?[- ]friendly|planet[- ]friendly|earth[- ]friendly|sustainabl|"
                      r"carbon[- ]neutral|net[- ]zero|\bgreen\b|zero[- ]waste|plastic[- ]neutral|100\s?%\s*biodegradab", re.I)
_ENV_SCOPE = re.compile(r"\b(bottle|pack|packaging|cap|label|refill|carton|wrapper|\d+\s?%\s*recycled)\b", re.I)
_NAT_HIGH = re.compile(r"100\s?%\s*(natural|pure)|\b(chemical|toxin)[- ]free\b|\bno\s+(chemicals|toxins)\b", re.I)
_NAT_FOOD = re.compile(r"\b(natural|pure|fresh|authentic|traditional|genuine|real|original)\b", re.I)
_HEALTH_DRINK = re.compile(r"\bhealth\s*drinks?\b", re.I)
_HEALTH_FN = re.compile(r"\bimmunity\b|\btaller\b|\bsharper\b|\bmemory\b|\bbrain\b|\bcholesterol\b|\bcures?\b|\bprevents?\b", re.I)
_SCI = re.compile(r"\b(clinically|scientifically)\s+proven\b|\b(recommended|approved|endorsed)\s+by\b|"
                  r"\b(dentists?|doctors?|dermatologists?)\b.*\brecommend", re.I)


def assess(c: Claim, category: str) -> tuple[str, str]:
    t, s, q, sd = c.claim_type, c.text, c.qualifier, c.source_date
    if t == "puffery":
        return "low", "Subjective praise; not a measurable claim."
    if t == "efficacy":
        if _SPF.match(s):
            return "low", "Standard SPF/PA statement."
        if not (_NUM.search(s) or _ABS.search(s)):
            return "low", "Unquantified efficacy claim."
        if not q:
            return "high", ("Absolute efficacy claim (100% / all / complete) with no stated test basis."
                            if _ABS.search(s) else "Quantified efficacy claim with no stated test basis.")
        return ("medium", "Test basis stated but no source or date.") if not sd else ("low", "Stated basis and date.")
    if t == "comparative":
        if _DENIG.search(s):
            return "high", "Comparison denigrates competitors."
        if _OWN.search(s) and q:
            return "low", "Comparison with own earlier formula, basis stated."
        if not q:
            return "high", "Comparison with no stated basis."
        return ("medium", "Basis stated but no source or date.") if not sd else ("low", "Basis with source and date.")
    if t in ("leadership", "awards_rankings"):
        if q and sd:
            return "low", "Source and period stated."
        return ("medium", "Source or period missing.") if (q or sd) else ("high", "No source or period for the claim.")
    if t == "appearance":
        if _SOCIAL.search(s):
            return "high", "Links appearance to social or professional success."
        if _FAIR.search(s) and not q:
            return "high", "Fairness/whitening framing with no study basis."
        if q:
            return ("low", "Study basis and date stated.") if sd else ("medium", "Study basis but no date/source.")
        return ("high", "Quantified appearance change with no study.") if _NUM.search(s) else \
            ("medium", "Appearance claim with no stated basis.")
    if t == "time_bound":
        if q:
            return ("low", "Study basis and date stated.") if sd else ("medium", "Qualified but no study date.")
        return "high", "Result promised within a time with no study basis."
    if t in ("scientific", "celebrity_endorsement"):
        if q and sd:
            return "low", "Source and date stated."
        if _SCI.search(s) or t == "celebrity_endorsement":
            return "high", "Clinical proof or expert endorsement asserted without a source."
        return "medium", "Testing claim without a source."
    if t == "environmental":
        if q:
            return "low", "Scoped with a stated basis."
        if _ENV_ABS.search(s):
            return "high", "Vague or absolute environmental claim without scope or disclosure."
        return "medium", "Environmental claim needs scope and substantiation."
    if t == "natural_purity":
        if _NAT_HIGH.search(s) and not q:
            return "high", "Absolute natural/free-from claim."
        if category == "food" and _NAT_FOOD.search(s):
            return "medium", "Restricted descriptive word on a food label."
        return "low", "Ingredient-level natural claim."
    if t == "nutrition_health":
        if _HEALTH_DRINK.search(s):
            return "high", "'Health drink' is not a permitted food category."
        if q:
            return "low", "Tied to a stated basis."
        if _HEALTH_FN.search(s):
            return "high", "Health-function claim (growth, immunity, memory, disease) without a permitted basis."
        return "medium", "Nutrient claim; thresholds apply."
    if t == "pricing_offer":
        return "low", "Price/offer statement."
    return "low", "No rule matched."


_SENT = re.compile(r"(?<=[.;])\s+")
_TOK = re.compile(r"[a-z0-9%]+")


def best_quote(text: str, query: str, min_len: int = 20) -> str:
    sents = [s for s in _SENT.split(text.strip()) if len(s) >= min_len] or [text.strip()]
    q = set(_TOK.findall(query.lower()))
    return max(enumerate(sents), key=lambda x: (len(q & set(_TOK.findall(x[1].lower()))), -x[0]))[1]


def cite(cl: dict, quote: str) -> Citation:
    return Citation(clause_id=cl["clause_id"], doc_id=cl["doc_id"], doc_title=cl["doc_title"],
                    section_path=cl["section_path"], number=cl.get("number"), page=cl["page_start"], quote=quote,
                    source=cl.get("source", "text"), ocr_conf=cl.get("ocr_conf"))


def rule_judge(claims: list[Claim], retrieved: list[list[dict]], category: str) -> list[Flag | None]:
    out: list[Flag | None] = []
    for c, rs in zip(claims, retrieved):
        risk, reason = assess(c, category)
        if risk == "low" or not rs:
            out.append(None)
            continue
        q = f"{c.text} {c.claim_type}"
        out.append(Flag(claim=c, risk=risk, reason=reason, evidence_span=c.text, judge="rule", confidence=None,
                        citations=[cite(cl, best_quote(cl["text"], q)) for cl in rs[:2]],
                        rewrite=None))
    return out


# ---------------------------------------------------------------- LLM judge
def llm_judge(llm, text: str, claims: list[Claim], retrieved: list[list[dict]], surface: str, category: str,
              definitions: str = "", memory: str = "") -> list[Flag | None]:
    if not claims:
        return []
    blocks = []
    for i, (c, rs) in enumerate(zip(claims, retrieved)):
        cl = "\n".join(f"  [{r['clause_id']}] ({r['doc_title']}; {r['section_path']}; p.{r['page_start']}) {r['text']}"
                       for r in rs) or "  (none)"
        blocks.append(f"CLAIM {i} (type={c.claim_type}; qualified={c.qualifier}; sourced={c.source_date}"
                      + (f"; footnote={c.footnote_text!r}" if c.footnote_text else "") + f"): {c.text}\n"
                      f"CLAUSES FOR CLAIM {i}:\n{cl}")
    prompt = render("judge", memory_examples=memory or "(none)", definitions=definitions or "(none)",
                    surface=surface, category=category, text=text, claims_with_clauses="\n\n".join(blocks))
    out = llm.json("judge", prompt, JudgeOut, step="judge")
    flags: list[Flag | None] = [None] * len(claims)
    for a in out.assessments:
        if not (0 <= a.claim_index < len(claims)) or a.risk == "low":
            continue
        by_id = {r["clause_id"]: r for r in retrieved[a.claim_index]}
        cits = []
        for ct in a.citations:
            r = by_id.get(ct.clause_id)
            cits.append(cite(r, ct.quote) if r else Citation(clause_id=ct.clause_id, quote=ct.quote))
        flags[a.claim_index] = Flag(claim=claims[a.claim_index], risk=a.risk, reason=a.reason,
                                    evidence_span=a.evidence_span, citations=cits, rewrite=a.rewrite,
                                    confidence=round(a.confidence, 3), judge="llm")
    return flags
