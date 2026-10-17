"""Audit agent chain (plain Python, typed steps, each logged):
normalise -> extract (LLM) || rules -> merge -> retrieve per claim -> judge (LLM | rule fallback)
-> citation guard (code) -> verifier (other model, only lowers) -> rewriter -> calibrator.

If the LLM fails anywhere before judging, the whole audit falls back to the rule extractor + rule judge and the
result says so (fallback_used + reason), so the UI can show "AI unavailable, showing rule-based result"."""
from __future__ import annotations

import time
from typing import Callable

from ..config import settings
from ..kb.clauses import clauses_by_id, load_store
from ..llm.client import LLMError
from ..retrieval.search import retrieve
from . import rewrite as rw
from . import verifier as vf
from .calibrate import Calibrator
from .extract import extract_llm
from .judge import assess, llm_judge, rule_judge
from .merge import merge
from .models import AuditOutput, Dropped, Flag
from .rule_extract import disclosure_claim, extract_rules
from .verify import guard

STEPS = ["Reading", "Finding claims", "Finding rules", "Judging", "Checking"]


def _defs_for(text: str) -> str:
    defs = load_store().get("definitions", {})
    low = text.lower()
    hits = [d for t, d in defs.items() if len(t) > 3 and t in low][:6]
    store = clauses_by_id()
    return "\n".join(f'- "{d["term"]}" ({d["doc_id"]}, {d["clause_id"]}): {store[d["clause_id"]]["text"][:300]}'
                     for d in hits if d["clause_id"] in store)


def audit(text: str, surface: str = "ecommerce", category: str = "home", paid: bool = False, llm=None,
          verifier_llm=None, hybrid: bool = True, use_verifier: bool = True, use_rerank: bool = True,
          use_memory: bool = True, on_step: Callable[[str, str, int], None] | None = None,
          db_url: str | None = None, log: Callable[[dict], None] | None = None) -> AuditOutput:
    t_all, out = time.time(), AuditOutput(text=text)
    text = text[: settings()["app"]["max_input_chars"]]
    out.text = text

    def step(name: str, fn):
        t0 = time.time()
        if on_step:
            on_step(name, "running", 0)
        try:
            r = fn()
            ms = int((time.time() - t0) * 1000)
            out.steps.append({"name": name, "status": "done", "ms": ms})
            if on_step:
                on_step(name, "done", ms)
            return r
        except Exception:
            out.steps.append({"name": name, "status": "error", "ms": int((time.time() - t0) * 1000)})
            if on_step:
                on_step(name, "error", 0)
            raise

    step("Reading", lambda: None)
    memory_text = ""

    def find_claims():
        nonlocal memory_text
        rules = extract_rules(text)
        if llm is None:
            return merge([], rules)
        if use_memory:
            from ..learning.memory import examples_text
            memory_text = examples_text([c.text for c in rules] or [text[:200]], db_url=db_url)
        try:
            ll = extract_llm(llm, text, surface, category, paid, memory_text)
        except LLMError as e:
            out.fallback_used, out.fallback_reason = True, f"claim extraction: {e}"
            return merge([], rules)
        return merge(ll, rules if hybrid else [])
    claims = step("Finding claims", find_claims)
    out.claims = claims

    def find_rules():
        rl = None if out.fallback_used else llm
        return [retrieve(c.text, c.claim_type, category, surface, llm=rl, use_rerank=use_rerank) for c in claims]
    retrieved = step("Finding rules", find_rules)
    out.not_covered = [c for c, r in zip(claims, retrieved) if not r and c.claim_type != "puffery"]
    judged = [(c, r) for c, r in zip(claims, retrieved) if r]
    jc, jr = [c for c, _ in judged], [r for _, r in judged]

    def judge_all():
        if llm is not None and not out.fallback_used and jc:
            try:
                return llm_judge(llm, text, jc, jr, surface, category, _defs_for(text), memory_text)
            except LLMError as e:
                out.fallback_used, out.fallback_reason = True, f"judge: {e}"
        return rule_judge(jc, jr, category)
    raw = step("Judging", judge_all)

    def check():
        kept: list[Flag] = []
        for c, r, f in zip(jc, jr, raw):
            if f is None:
                out.low_risk.append(c)
                continue
            rule_risk, _ = assess(c, category)
            g, d = guard(f, text, r, rule_risk)
            if d:
                out.dropped.append(d)
            else:
                kept.append(g)
        # deterministic #ad disclosure check (paid social posts)
        disc = disclosure_claim(text, surface, paid)
        if disc:
            dc, risk, reason = disc
            rs = retrieve("influencer paid promotion disclosure label #ad sponsored", "disclosure", category, surface)
            if rs:
                from .judge import best_quote, cite
                f = Flag(claim=dc, risk=risk, reason=reason, evidence_span=dc.text, judge="rule",
                         citations=[cite(rs[0], best_quote(rs[0]["text"], "disclosure label ad paid promotion"))])
                g, d = guard(f, text, rs, risk)
                (kept.append(g) if g else out.dropped.append(d))
                out.claims.append(dc)
            else:
                out.not_covered.append(dc)
        if use_verifier and verifier_llm is not None and not out.fallback_used:
            llm_flags = [f for f in kept if f.judge == "llm"]
            try:
                verdicts = vf.verify_flags(verifier_llm, text, llm_flags, clauses_by_id())
                vk, low, dr = vf.apply(llm_flags, verdicts)
                kept = [f for f in kept if f.judge != "llm"] + vk
                out.low_risk += low
                out.dropped += dr
            except LLMError as e:
                out.dropped.append(Dropped(claim="(verifier)", reason=f"verifier unavailable: {e}", stage="verifier"))
        rw.rewrite(None if out.fallback_used else llm, text, kept)
        cal = Calibrator(db_url)
        for f in kept:
            f.confidence = cal(f.confidence, f.claim.claim_type)
        order = {"high": 0, "medium": 1, "low": 2}
        kept.sort(key=lambda f: (order[f.risk], f.claim.start))
        return kept
    out.flags = step("Checking", check)
    out.steps.append({"name": "total", "status": "done", "ms": int((time.time() - t_all) * 1000)})
    return out
