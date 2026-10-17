"""A tiny made-up knowledge base for tests (never the real clause store)."""
from __future__ import annotations

import json

from claimguard import config
from claimguard.kb import clauses as cl
from claimguard.retrieval import index, search


def clause(cid, doc, text, types, cats=("all",), surfaces=("all",), page=1, ocr_conf=None, section=""):
    return {"clause_id": cid, "doc_id": doc, "regulator": doc.split("-")[0], "doc_title": f"Made-up {doc}",
            "section_path": section or cid, "number": cid.split("-")[-1], "title": text[:40], "text": text,
            "page_start": page, "page_end": page, "source": "ocr" if ocr_conf else "text", "ocr_conf": ocr_conf,
            "hash": cid, "duplicate_of": None, "claim_types": list(types), "categories": list(cats),
            "surfaces": list(surfaces), "administrative": False, "enabled": True, "tag_source": "manual",
            "tag_check": []}


DEFAULT = [
    clause("MC-1.1", "MC", "Advertisements must be truthful. All claims about made-up performance must be capable of "
           "substantiation by the advertiser with a repeatable test.", ["efficacy", "general_truthfulness"]),
    clause("MC-4.1", "MC", "Comparisons with other made-up products must state the basis of comparison clearly and "
           "must not unfairly denigrate a competitor.", ["comparative"]),
    clause("MG-1", "MG", "Vague environmental claims such as eco-friendly or green must carry a clear qualifier "
           "explaining the exact made-up environmental benefit.", ["environmental"]),
    clause("MF-4", "MF", "A made-up food label shall not call a beverage a health drink or claim it makes children "
           "taller without a permitted basis.", ["nutrition_health"], cats=("food",)),
    clause("MI-1", "MI", "Influencers must place a clear disclosure label such as #ad at the start of every paid "
           "made-up promotion post.", ["disclosure"], surfaces=("social_post",)),
    clause("MS-2", "MS", "Scanned made-up rule: clinical proof claims need a named study and date before publication.",
           ["scientific", "time_bound"], ocr_conf=0.7),
]


def make_kb(tmp_path, monkeypatch, clauses=None):
    clauses = clauses or [dict(c) for c in DEFAULT]
    s = config.settings()
    monkeypatch.setitem(s["paths"], "build", tmp_path)
    (tmp_path / "clauses.json").write_text(json.dumps({"clauses": clauses, "definitions": {}, "edges": []}))
    cl.load_store.cache_clear()
    search._cache.cache_clear()
    index.build_index(clauses, dense=False)
    monkeypatch.setattr(index, "dense_table", lambda: (_ for _ in ()).throw(RuntimeError("no dense in tests")))
    return clauses
