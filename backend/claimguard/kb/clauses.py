"""Clause store: segmentation -> dedupe -> tags/scope -> definitions/xrefs -> knowledge/build/clauses.json."""
from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

import yaml

from ..config import ROOT, path
from .ingest import load_pages, sources
from .segment import dedupe, norm, segment_doc
from .tagger import apply_tags, llm_tag
from .xref import cross_refs, definitions

STORE = lambda: path("build") / "clauses.json"  # noqa: E731


def build_clauses(pages: list[dict] | None = None, tag: bool = True, llm=None) -> list[dict]:
    pages = pages or load_pages()
    srcs = sources()
    clauses = []
    for s in srcs:
        clauses += segment_doc(s, [p for p in pages if p["doc_id"] == s["id"]])
    dedupe(clauses)
    if tag:
        try:
            if llm is None:
                from ..llm.client import LLMClient
                llm = LLMClient()
            n = llm_tag(clauses, llm)
            print(f"LLM-tagged {n} new clauses")
        except Exception as e:  # no key: cached or keyword tags
            print(f"LLM tagging unavailable ({str(e)[:80]}); using cached/keyword tags")
    apply_tags(clauses, srcs)
    data = {"clauses": clauses, "definitions": definitions(clauses), "edges": cross_refs(clauses)}
    STORE().parent.mkdir(parents=True, exist_ok=True)
    STORE().write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    load_store.cache_clear()
    return clauses


@lru_cache(maxsize=1)
def load_store() -> dict:
    return json.loads(STORE().read_text(encoding="utf-8"))


def clauses_by_id() -> dict[str, dict]:
    return {c["clause_id"]: c for c in load_store()["clauses"]}


def spot_checks(clauses: list[dict] | None = None) -> list[dict]:
    clauses = clauses or load_store()["clauses"]
    chk = yaml.safe_load((ROOT / "knowledge/checks/spot_checks.yaml").read_text(encoding="utf-8"))["checks"]
    out = []
    for c in chk:
        t = norm(c["text"])
        hit = next((x for x in clauses if t in norm(x["text"])), None)
        out.append({**c, "found": hit is not None, "clause_id": hit and hit["clause_id"],
                    "found_page": hit and hit["page_start"]})
    return out


def clause_gates(clauses: list[dict]) -> list[str]:
    problems = []
    pages = {(p["doc_id"], p["page"]): p for p in load_pages()}
    for c in clauses:
        for pg in range(c["page_start"], c["page_end"] + 1):
            p = pages.get((c["doc_id"], pg))
            if p and p["method"] == "excluded" and p["script"] == "hi_legacy":
                problems.append(f"{c['clause_id']} comes from legacy-Hindi page {pg}")
    ccpa = [c for c in clauses if c["doc_id"] == "CCPA-GW"]
    confs = [c["ocr_conf"] for c in ccpa if c["ocr_conf"] is not None]
    if len(ccpa) < 8 or (confs and sum(confs) / len(confs) < 0.85):
        problems.append(f"CCPA-GW: {len(ccpa)} clauses, mean OCR conf {sum(confs) / max(1, len(confs)):.2f}")
    miss = [s for s in spot_checks(clauses) if not s["found"]]
    problems += [f"spot check not found: {s['doc']} p.{s['page']} {s['text'][:60]}" for s in miss]
    return problems


def clause_report(clauses: list[dict]) -> str:
    by = Counter(c["doc_id"] for c in clauses)
    lines = ["## Clauses", "", "| Document | Clauses | Enabled | From OCR | Low OCR conf (<0.80) | Untagged | Duplicates |",
             "|---|---|---|---|---|---|---|"]
    for d, n in by.items():
        cs = [c for c in clauses if c["doc_id"] == d]
        lines.append(f"| {d} | {n} | {sum(c['enabled'] for c in cs)} | {sum(c['source'] == 'ocr' for c in cs)} | "
                     f"{sum((c['ocr_conf'] or 1) < 0.8 for c in cs)} | "
                     f"{sum(c['enabled'] and not c['claim_types'] for c in cs)} | {sum(bool(c['duplicate_of']) for c in cs)} |")
    src = Counter(c["tag_source"] for c in clauses)
    sc = spot_checks(clauses)
    lines += ["", f"Tags from: {dict(src)}. LLM tags without keyword support (check): "
              f"{sum(bool(c['tag_check']) for c in clauses)}.",
              f"Spot checks: {sum(s['found'] for s in sc)}/{len(sc)} found verbatim."]
    return "\n".join(lines)
