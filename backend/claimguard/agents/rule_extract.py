"""Rule extractor (safety net): sentence split + taxonomy triggers + footnote/qualifier detection (ported from v1).
Also the deterministic #ad disclosure check for paid social posts."""
from __future__ import annotations

import re

from .models import Claim
from .taxonomy import QUALIFIER, YEAR, classify

_ABBR = re.compile(r"\b(vs|No|no|e\.g|i\.e|Rs|approx|incl|excl|Dr|St|Ltd|Pvt|Co|etc)\.", re.I)
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9*^#(\"'])|\n+|\s*[•·▪●|]\s*")
_DECLARATION = re.compile(r"^(generic\s+name|common\s+name|net\s*(qty|quantity|wt|weight|content|vol)|m\.?r\.?p|"
                          r"unit\s+sale\s+price|(manufactured|marketed|packed|imported)\s+by|(consumer|customer)\s+care|"
                          r"country\s+of\s+origin|best\s+before|batch|use\s+code|link\s+in\s+bio)", re.I)
DISCLOSURE = re.compile(r"#(ad|advertisement|sponsored|collab|collaboration|partnership|paidpartnership|employee|"
                        r"freegift|gifted)\b|\bpaid\s+partnership\b", re.I)


def split_sentences(text: str) -> list[tuple[int, str]]:
    masked = _ABBR.sub(lambda m: m.group(0).replace(".", "․"), text)
    out, start = [], 0
    for m in _BOUNDARY.finditer(masked):
        _add(out, text, start, m.start())
        start = m.end()
    _add(out, text, start, len(text))
    return out


def _add(out, text, a, b):
    seg = text[a:b]
    s = seg.strip()
    if s:
        out.append((a + seg.index(s), s))


def footnotes(text: str) -> list[str]:
    return [s for _, s in split_sentences(text) if s.startswith(("*", "^"))]


def qualifier_status(sentence: str, notes: list[str]) -> tuple[bool, bool]:
    """(has_qualifier, has_source_date). A '*'/'^' marker counts only when a qualifying footnote exists."""
    if QUALIFIER.search(sentence):
        return True, bool(YEAR.search(sentence))
    for mark in ("*", "^"):
        if mark in sentence:
            for n in notes:
                if n.startswith(mark) and QUALIFIER.search(n):
                    return True, bool(YEAR.search(n))
    return False, False


def sentence_at(text: str, pos: int) -> str:
    for off, s in split_sentences(text):
        if off <= pos < off + len(s):
            return s
    return ""


def extract_rules(text: str) -> list[Claim]:
    notes = footnotes(text)
    out = []
    for off, sent in split_sentences(text):
        if sent.startswith(("*", "^")) or _DECLARATION.match(sent):
            continue
        t = classify(sent)
        if not t:
            continue
        q, sd = qualifier_status(sent, notes)
        out.append(Claim(text=sent, start=off, end=off + len(sent), claim_type=t, source="rule", qualifier=q,
                         source_date=sd))
    return out


def disclosure_claim(text: str, surface: str, paid: bool, window: int = 200) -> tuple[Claim, str, str] | None:
    """Paid social post without a disclosure label near the start -> (claim, risk, reason)."""
    if surface != "social_post" or not paid:
        return None
    m = DISCLOSURE.search(text)
    if m and m.start() <= window:
        return None
    head = text.strip()[:80]
    if len(text.strip()) > 80 and not text.strip()[80].isspace():
        head = head.rsplit(" ", 1)[0]
    s = text.find(head)
    claim = Claim(text=head, start=s, end=s + len(head), claim_type="disclosure", source="rule")
    if m:
        return claim, "medium", f"Disclosure label '{m.group(0)}' appears only after the first {window} characters."
    return claim, "high", "Paid promotion with no disclosure label (#ad, #collab, #sponsored, #partnership)."
