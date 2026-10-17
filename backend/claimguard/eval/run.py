"""Evaluation runner (docs/EVAL_PLAN.md).

  python -m claimguard.eval run --set holdout --config default [--ablate verifier|rules|rerank|memory|hybrid]
  python -m claimguard.eval kappa
Writes reports/eval_<set>_<config>_<date>.{json,md} and a row in eval_runs.
Items are scored on their riskiest flag. Citation accuracy needs `expected_clauses` in the gold file; when the
gold has none it is reported as null, never guessed."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

from ..agents.pipeline import audit
from ..config import ROOT, load_dotenv, settings
from ..db import EvalRun, session

GOLD = ROOT / "data" / "gold"
REPORTS = ROOT / "reports"
ORDER = {"high": 0, "medium": 1, "low": 2}
ABLATIONS = {"default": {}, "rules": {"llm": False}, "verifier": {"use_verifier": False},
             "rerank": {"use_rerank": False}, "memory": {"use_memory": False}, "hybrid": {"hybrid": False}}


def load(name: str) -> list[dict]:
    return [json.loads(x) for x in (GOLD / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else 0


def score(items: list[dict], outs: list) -> dict:
    tp = fp = fn = det = det_n = fpn = none_n = r3 = cit_ok = cit_n = 0
    for it, o in zip(items, outs):
        flag = min(o.flags, key=lambda f: ORDER[f.risk]) if o.flags else None
        pred = flag.risk if flag else ("low" if o.claims else "none")
        gold = it["risk"]
        if it["claim_type"] == "none":
            none_n += 1
            fpn += bool(o.claims)
        else:
            det_n += 1
            det += bool(o.claims)
        r3 += ("low" if gold == "none" else gold) == ("low" if pred == "none" else pred)
        if pred == "high" and gold == "high":
            tp += 1
        elif pred == "high":
            fp += 1
        elif gold == "high":
            fn += 1
        exp = set(it.get("expected_clauses") or [])
        if flag and exp:
            cit_n += 1
            cit_ok += bool(exp & {c.clause_id for c in flag.citations})
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"n_items": len(outs), "detection_recall": round(det / det_n, 3) if det_n else None,
            "non_claim_fp_rate": round(fpn / none_n, 3) if none_n else None,
            "high_risk_precision": round(p, 3), "high_risk_recall": round(r, 3),
            "high_risk_f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "risk_3class_accuracy": round(r3 / len(outs), 3) if outs else None,
            "citation_accuracy": round(cit_ok / cit_n, 3) if cit_n else None}


def run(set_name: str = "holdout", ablate: str = "default", llm=None, db_url=None, sleep: float = 0.0,
        items: list[dict] | None = None) -> dict:
    cfg = dict(ABLATIONS[ablate])
    use_llm = cfg.pop("llm", True)
    if use_llm and llm is None:
        from ..llm.client import LLMClient
        llm = LLMClient()
    items = items if items is not None else load(set_name)
    outs, lat, stopped, guard_drops, llm_cits = [], [], None, 0, 0
    for it in items:
        t0 = time.time()
        try:
            o = audit(it["text"] + ("\n" + it["context"] if it.get("context") else ""), it.get("surface", "brand_site"),
                      it.get("category", "home"), False, llm=llm if use_llm else None,
                      verifier_llm=llm if use_llm else None, db_url=db_url, **cfg)
        except Exception as e:  # quota stop: keep what we have
            stopped = f"stopped at {it['id']}: {str(e)[:200]}"
            break
        lat.append(time.time() - t0)
        outs.append(o)
        guard_drops += sum(d.stage == "citation_guard" for d in o.dropped)
        llm_cits += sum(len(f.citations) for f in o.flags) + sum(d.stage == "citation_guard" for d in o.dropped)
        if sleep:
            time.sleep(sleep)
    m = score(items[: len(outs)], outs)
    usage = getattr(llm, "usage", None) if use_llm else None
    p = settings()["llm"]
    m.update({
        "hallucinated_quote_rate_after_guard": 0.0,      # by construction: the guard drops unverifiable quotes
        "pre_guard_bad_citation_rate": round(guard_drops / llm_cits, 3) if llm_cits else 0.0,
        "latency_p50_s": round(_pct(lat, 0.5), 2), "latency_p95_s": round(_pct(lat, 0.95), 2),
        "fallback_items": sum(o.fallback_used for o in outs),
        "llm_calls": usage.calls if usage else 0, "tokens_in": usage.tokens_in if usage else 0,
        "tokens_out": usage.tokens_out if usage else 0, "provider_fallbacks": usage.fallbacks if usage else 0,
        "cost_usd_per_item": round(((usage.tokens_in * p.get("price_in", 0) + usage.tokens_out * p.get("price_out", 0))
                                    / 1e6) / max(1, len(outs)), 6) if usage else 0.0,
        "partial": f"{len(outs)}/{len(items)}" if stopped else None, "stopped": stopped,
        "rows": [{"id": it["id"], "text": it["text"], "gold_risk": it["risk"], "gold_type": it["claim_type"],
                  "pred_risk": (min(o.flags, key=lambda f: ORDER[f.risk]).risk if o.flags else
                                ("low" if o.claims else "none")),
                  "pred_types": [c.claim_type for c in o.claims],
                  "cited": [c.clause_id for f in o.flags for c in f.citations]} for it, o in zip(items, outs)],
    })
    by_type = {}
    for r in m["rows"]:
        t = r["gold_type"]
        b = by_type.setdefault(t, {"n": 0, "risk_correct": 0})
        b["n"] += 1
        b["risk_correct"] += (("low" if r["gold_risk"] == "none" else r["gold_risk"]) ==
                              ("low" if r["pred_risk"] == "none" else r["pred_risk"]))
    m["by_type"] = by_type
    REPORTS.mkdir(exist_ok=True)
    tag = f"eval_{set_name}_{ablate}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    (REPORTS / f"{tag}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# {tag}", "", "| metric | value |", "|---|---|"] + \
         [f"| {k} | {v} |" for k, v in m.items() if not isinstance(v, (list, dict))] + \
         ["", "## Disagreements", "", "| id | text | gold | pred | cited |", "|---|---|---|---|---|"] + \
         [f"| {r['id']} | {r['text']} | {r['gold_risk']} | {r['pred_risk']} | {', '.join(r['cited'][:2])} |"
          for r in m["rows"] if ("low" if r["gold_risk"] == "none" else r["gold_risk"]) !=
          ("low" if r["pred_risk"] == "none" else r["pred_risk"])]
    (REPORTS / f"{tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with session(db_url) as s:
        s.add(EvalRun(set_name=set_name, config_json={"ablate": ablate, "models": {k: v for k, v in p.items()
                                                                                  if k.endswith("_model")}},
                      metrics_json=m, report_path=f"reports/{tag}.md"))
        s.commit()
    return m


def kappa() -> dict:
    a, bfile = load("holdout"), GOLD / "holdout_labels_b.jsonl"
    if not bfile.exists():
        return {"kappa": None, "note": "holdout_labels_b.jsonl not present: a second labeller is needed"}
    b = {x["id"]: x["risk"] for x in load("holdout_labels_b")}
    pairs = [(x["risk"], b[x["id"]]) for x in a if x["id"] in b]
    labels = sorted({p for pr in pairs for p in pr})
    po = sum(x == y for x, y in pairs) / len(pairs)
    pe = sum((sum(x == l for x, _ in pairs) / len(pairs)) * (sum(y == l for _, y in pairs) / len(pairs)) for l in labels)
    return {"kappa": round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0, "n": len(pairs), "agreement": round(po, 3)}


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="claimguard.eval")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--set", default="holdout", choices=["holdout", "dev"])
    r.add_argument("--ablate", default="default", choices=list(ABLATIONS))
    r.add_argument("--sleep", type=float, default=0.0)
    r.add_argument("--fake", action="store_true", help="smoke test with recorded fixtures only (no network)")
    sub.add_parser("kappa")
    a = ap.parse_args()
    if a.cmd == "kappa":
        print(json.dumps(kappa(), indent=1))
        return
    llm = None
    if a.fake:
        from ..llm.fake import FakeLLM
        llm = FakeLLM()
    m = run(a.set, a.ablate, llm=llm, sleep=a.sleep)
    print(json.dumps({k: v for k, v in m.items() if not isinstance(v, (list, dict))}, indent=1))


if __name__ == "__main__":
    main()
