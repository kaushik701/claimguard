"""Clause tagging: LLM (P1, batched) with a fixed label set, cross-checked by keyword rules, then scope rules
(sources.yaml + overrides/scope.yaml) and human overrides (overrides/tags.yaml) applied last.

LLM tags are cached by clause hash in knowledge/tag_cache.json (committed), so rebuilds are free and identical
without a key. Without a key and without a cache entry, keyword tags are used (tag_source = "keyword")."""
from __future__ import annotations

import json
import re

import yaml

from ..config import ROOT
from ..llm.prompts import render
from ..llm.schemas import TAG_CATEGORIES, TAG_SURFACES, TAG_TYPES, TagBatchOut

CACHE = ROOT / "knowledge" / "tag_cache.json"
OVERRIDES = ROOT / "knowledge" / "overrides"

KEYWORDS: dict[str, list[str]] = {
    "efficacy": ["efficacy", "performance", "germ", "bacteria", "kills", "protection", "effective", "removes"],
    "comparative": ["compar", "competitor", "denigrat", "superior", "rival"],
    "leadership": ["no. 1", "no.1", "number one", "leader", "leadership", "largest", "best-selling", "market share"],
    "time_bound": ["instant", "immediate", "overnight", "within days", "in 7 days"],
    "appearance": ["skin", "fair", "complexion", "whiten", "lighten", "appearance", "cosmetic", "hair"],
    "scientific": ["research", "clinical", "scientific", "study", "studies", "expert", "doctor", "laborator",
                   "test"],
    "environmental": ["environment", "eco", "green", "sustainab", "recycl", "biodegrad", "carbon", "greenwash",
                      "planet", "compostab"],
    "natural_purity": ["natural", "pure", "fresh", "organic", "free from", "-free", "authentic", "traditional"],
    "nutrition_health": ["nutrient", "nutrition", "health claim", "health drink", "vitamin", "protein", "fortif",
                         "immunity", "dietary", "food", "sugar", "fat"],
    "disclosure": ["influencer", "disclos", "#ad", "paid partnership", "sponsor", "material connection"],
    "pricing_offer": ["price", "offer", "discount", "free gift", "saving", "cheaper"],
    "celebrity_endorsement": ["celebrit", "endorse", "testimonial"],
    "awards_rankings": ["award", "ranking", "rank"],
    "children": ["child", "children", "kids", "minor"],
    "gender": ["gender", "stereotyp", "women", "men "],
    "general_truthfulness": ["truthful", "substantiat", "mislead", "honest", "exaggerat", "accurate"],
}
_KW = {t: re.compile("|".join(r"(?<![a-z])" + re.escape(k) for k in ks), re.I) for t, ks in KEYWORDS.items()}


def keyword_tags(text: str) -> list[str]:
    return [t for t, rx in _KW.items() if rx.search(text)]


def _cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def _clean(out) -> dict:
    return {"claim_types": [t for t in out.claim_types if t in TAG_TYPES],
            "categories": [c for c in out.categories if c in TAG_CATEGORIES] or ["all"],
            "surfaces": [s for s in out.surfaces if s in TAG_SURFACES] or ["all"],
            "administrative": out.administrative, "rationale": out.rationale}


def llm_tag(clauses: list[dict], llm, batch: int = 10, max_chars: int = 700) -> int:
    """Tag clauses missing from the cache; returns how many were tagged now. Stops cleanly on LLMError."""
    from ..llm.client import LLMError
    cache = _cache()
    todo = [c for c in clauses if c["hash"] not in cache]
    done = 0
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        block = "\n\n".join(f"[{c['clause_id']}] ({c['doc_title']} | {c['section_path']})\n{c['text'][:max_chars]}"
                            for c in part)
        try:
            out = llm.json("clause_tagger_batch", render("clause_tagger_batch", clauses_block=block), TagBatchOut,
                           step="tagger")
        except LLMError as e:
            print(f"tagging stopped: {e}")
            break
        by_id = {c["clause_id"]: c for c in part}
        for it in out.items:
            if it.clause_id in by_id:
                cache[by_id[it.clause_id]["hash"]] = _clean(it)
                done += 1
        CACHE.write_text(json.dumps(cache, indent=0, ensure_ascii=False), encoding="utf-8")
    return done


def apply_tags(clauses: list[dict], sources: list[dict]) -> None:
    cache = _cache()
    scope = (yaml.safe_load((OVERRIDES / "scope.yaml").read_text(encoding="utf-8")) or {}).get("rules", [])
    overrides = yaml.safe_load((OVERRIDES / "tags.yaml").read_text(encoding="utf-8")) or {}
    doc_scope = {s["id"]: s.get("scope") or {} for s in sources}
    for c in clauses:
        kw = keyword_tags(f"{c['section_path']} {c['text']}")
        if c["hash"] in cache:
            t = cache[c["hash"]]
            c.update(claim_types=list(t["claim_types"]), categories=list(t["categories"]),
                     surfaces=list(t["surfaces"]), administrative=t["administrative"], tag_source="llm",
                     tag_check=sorted(set(t["claim_types"]) - set(kw) - {"general_truthfulness"}))
        else:
            c.update(claim_types=kw, categories=["all"], surfaces=["all"], administrative=False,
                     tag_source="keyword", tag_check=[])
        ds = doc_scope.get(c["doc_id"], {})
        if "claim_types" in ds:
            c["claim_types"] = [t for t in c["claim_types"] if t in ds["claim_types"]] or list(ds["claim_types"])
        if "categories" in ds:
            c["categories"] = list(ds["categories"])
        if "surfaces" in ds:
            c["surfaces"] = list(ds["surfaces"])
        c["enabled"] = not c["administrative"]
        where = f"{c['doc_title']} {c['section_path']}".lower()
        for r in scope:
            if str(r["match"]).lower() in where:
                if "use" in r:
                    c["enabled"] = bool(r["use"])
                for k in ("categories", "surfaces", "claim_types"):
                    if k in r:
                        c[k] = list(r[k])
                        c["tag_source"] = "scope"
        if c["clause_id"] in overrides:
            o = overrides[c["clause_id"]] or {}
            for k in ("claim_types", "categories", "surfaces"):
                if k in o:
                    c[k] = list(o[k])
            if "enabled" in o:
                c["enabled"] = bool(o["enabled"])
            c["tag_source"] = "manual"


def save_override(clause_id: str, tags: dict) -> None:
    f = OVERRIDES / "tags.yaml"
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    data[clause_id] = {k: v for k, v in tags.items() if k in ("claim_types", "categories", "surfaces", "enabled")}
    f.write_text("# Human corrections to clause tags. Survive rebuilds.\n" +
                 yaml.safe_dump(data, sort_keys=True, allow_unicode=True), encoding="utf-8")
