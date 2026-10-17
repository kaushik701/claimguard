"""Hybrid retrieval: filters -> BM25 + dense -> reciprocal rank fusion -> 1-hop graph expansion -> LLM rerank.

retrieve() returns up to final_k clauses with scores; an empty list means "not covered by the knowledge base".
Query expansion (P4) and rerank (P5) use the LLM when given one and are cached by input."""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import path, settings
from ..kb.clauses import clauses_by_id, load_store
from ..llm.prompts import render
from ..llm.schemas import QueriesOut, RerankOut
from .index import dense_table, embed, load_bm25, tokenize

TYPE_HINT = {
    "efficacy": "performance efficacy claims substantiation test", "comparative": "comparison competitor denigration",
    "leadership": "leadership No.1 market leader claims source", "time_bound": "results within time substantiation",
    "appearance": "appearance skin fairness complexion", "scientific": "scientific clinical research expert claims",
    "environmental": "environmental green claims eco-friendly greenwashing", "natural_purity": "natural pure free from",
    "nutrition_health": "nutrition health claims food nutrient", "awards_rankings": "awards rankings",
    "pricing_offer": "price offer discount free", "celebrity_endorsement": "celebrity endorsement testimonial",
    "puffery": "obvious exaggeration puffery", "disclosure": "influencer disclosure label paid promotion",
}


def allowed(c: dict, claim_type: str | None, category: str | None, surface: str | None) -> bool:
    """Scope filter: enabled, not a duplicate, category / surface fit, claim type or general truthfulness."""
    if not c.get("enabled", True) or c.get("duplicate_of"):
        return False
    if category and not ({"all", category} & set(c.get("categories") or ["all"])):
        return False
    if surface and not ({"all", surface} & set(c.get("surfaces") or ["all"])):
        return False
    if claim_type:
        types = set(c.get("claim_types") or [])
        if claim_type not in types and "general_truthfulness" not in types:
            return False
    return True


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    score: dict[str, float] = {}
    for ranking in rankings:
        for r, cid in enumerate(ranking):
            score[cid] = score.get(cid, 0.0) + 1.0 / (k + r + 1)
    return sorted(score.items(), key=lambda x: -x[1])


def _cache_file():
    return path("build") / "llm_retrieval_cache.json"


@lru_cache(maxsize=1)
def _cache() -> dict:
    f = _cache_file()
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _cache_put(key: str, val) -> None:
    c = _cache()
    c[key] = val
    _cache_file().write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def expand(claim: str, claim_type: str, category: str, llm) -> list[str]:
    key = f"exp|{claim}|{claim_type}|{category}"
    if key in _cache():
        return _cache()[key]
    try:
        q = llm.json("query_expander", render("query_expander", claim=claim, claim_type=claim_type, category=category),
                     QueriesOut, step="expand").queries[:2]
    except Exception:
        return []
    _cache_put(key, q)
    return q


def candidates(query: str, ok: set[str], n: int, dense: bool = True) -> list[str]:
    """Fused clause ranking (BM25 + dense) restricted to allowed clause ids."""
    bm = load_bm25()
    scores = bm["bm25"].get_scores(tokenize(query))
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    bm_rank, seen = [], set()
    for i in order:
        cid = bm["chunks"][i]["clause_id"]
        if cid in ok and cid not in seen and scores[i] > 0:
            seen.add(cid)
            bm_rank.append(cid)
        if len(bm_rank) >= n:
            break
    rankings = [bm_rank]
    if dense:
        try:
            hits = dense_table().search(embed([query])[0]).limit(200).to_list()
            d_rank, seen = [], set()
            for h in hits:
                if h["clause_id"] in ok and h["clause_id"] not in seen:
                    seen.add(h["clause_id"])
                    d_rank.append(h["clause_id"])
                if len(d_rank) >= n:
                    break
            rankings.append(d_rank)
        except Exception:  # no vectors built (e.g. tests, --no-index): BM25 only
            pass
    return [cid for cid, _ in rrf(rankings, settings()["retrieval"]["rrf_k"])]


def rerank(claim: str, claim_type: str, category: str, surface: str, cands: list[dict], llm) -> list[tuple[str, int, str]]:
    key = f"rr|{claim}|{claim_type}|{category}|{surface}|{','.join(c['clause_id'] for c in cands)}"
    if key in _cache():
        return [tuple(x) for x in _cache()[key]]
    block = "\n\n".join(f"[{c['clause_id']}] ({c['doc_title']}; {c['section_path']}) {c['text'][:700]}" for c in cands)
    out = llm.json("reranker", render("reranker", claim=claim, claim_type=claim_type, category=category,
                                      surface=surface, numbered_clauses_with_ids_and_text=block), RerankOut,
                   step="rerank")
    valid = {c["clause_id"] for c in cands}
    res = [(r.clause_id, r.score, r.why) for r in out.ranked if r.clause_id in valid]
    _cache_put(key, res)
    return res


def retrieve(claim: str, claim_type: str | None, category: str | None = None, surface: str | None = None,
             llm=None, k: int | None = None, use_filter: bool = True, dense: bool | None = None,
             use_rerank: bool = True, use_expand: bool = True) -> list[dict]:
    cfg = settings()["retrieval"]
    k = k or cfg["final_k"]
    if dense is None:  # CLAIMGUARD_DENSE=0 on small hosts (e.g. Render free, 512 MB): BM25 + LLM rerank only
        import os
        dense = os.getenv("CLAIMGUARD_DENSE", "1") != "0"
    store = clauses_by_id()
    ok = {cid for cid, c in store.items() if allowed(c, claim_type if use_filter else None, category, surface)}
    if not ok:
        return []
    query = f"{claim} {TYPE_HINT.get(claim_type or '', '')}"
    rankings = [candidates(query, ok, cfg["bm25_k"], dense)]
    if llm is not None and use_expand:
        rankings += [candidates(q, ok, cfg["bm25_k"], dense) for q in expand(claim, claim_type or "", category or "", llm)]
    fused = [cid for cid, _ in rrf(rankings, cfg["rrf_k"])]
    if not fused and claim_type:  # no word/vector overlap: clauses tagged for exactly this claim type
        fused = sorted(cid for cid in ok if claim_type in (store[cid].get("claim_types") or []))
    # 1-hop graph expansion: clauses that top hits refer to
    edges = load_store().get("edges", [])
    extra = [b for a, b in edges if a in fused[:5] and b in ok and b not in fused]
    pool = (fused + extra)[: cfg["rerank_top"]]
    if llm is not None and use_rerank and pool:
        try:
            ranked = rerank(claim, claim_type or "", category or "", surface or "", [store[c] for c in pool], llm)
            keep = [(cid, s, why) for cid, s, why in ranked if s > cfg["not_covered_score"]]
            return [{**store[cid], "rerank_score": s, "rerank_why": why} for cid, s, why in keep[:k]]
        except Exception:
            pass  # rerank failed: fall back to fused order
    return [{**store[cid], "rerank_score": None, "rerank_why": ""} for cid in pool[:k]]
