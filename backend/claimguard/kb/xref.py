"""Definitions ("X" means ...) and cross-references ("clause 1.2", "regulation 4") as a small clause graph."""
from __future__ import annotations

import re

_DEF = re.compile(r"[“\"]([^”\"]{2,40})[”\"]\s+(?:means|shall mean|includes)", re.I)
_REF = re.compile(r"\b(?:clause|regulation|chapter|guideline|section)\s+(\d+(?:\.\d+)*)(?:\s*\((\d+)\))?", re.I)


def definitions(clauses: list[dict]) -> dict[str, dict]:
    """term (lower) -> {term, clause_id, doc_id}; first definition wins."""
    out: dict[str, dict] = {}
    for c in clauses:
        for m in _DEF.finditer(c["text"]):
            out.setdefault(m.group(1).lower(), {"term": m.group(1), "clause_id": c["clause_id"], "doc_id": c["doc_id"]})
    return out


def cross_refs(clauses: list[dict]) -> list[tuple[str, str]]:
    """(from_clause, to_clause) edges inside the same document, by number."""
    by_num = {(c["doc_id"], c["number"]): c["clause_id"] for c in clauses if c.get("number")}
    edges = []
    for c in clauses:
        for m in _REF.finditer(c["text"]):
            to = by_num.get((c["doc_id"], m.group(1)))
            if to and to != c["clause_id"]:
                edges.append((c["clause_id"], to))
    return sorted(set(edges))
