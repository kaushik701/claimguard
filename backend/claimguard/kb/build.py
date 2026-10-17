"""Knowledge build: pages -> clauses -> tags -> xrefs -> indexes, with quality gates and report.md.

  python -m claimguard.kb build [--no-ocr] [--doc ID] [--no-tag] [--no-index]
  python -m claimguard.kb check            # spot checks against the clause store
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import pandas as pd

from ..config import path
from .ingest import ingest_doc, sources


def build_pages(ocr: bool = True, only: str | None = None) -> list[dict]:
    pages = []
    for src in sources():
        if only and src["id"] != only:
            continue
        pages += ingest_doc(src, ocr=ocr)
    out = path("build")
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(pages).to_parquet(out / "pages.parquet", index=False)
    return pages


def page_gates(pages: list[dict]) -> list[str]:
    """Every page accounted for: method set, and excluded pages carry a reason."""
    problems = []
    expected = {s["id"]: s["pages"] for s in sources()}
    got = Counter(p["doc_id"] for p in pages)
    for d, n in expected.items():
        if d in got and got[d] != n:
            problems.append(f"{d}: {got[d]} pages read, sources.yaml says {n}")
    for p in pages:
        if p["method"] not in ("text", "ocr", "excluded"):
            problems.append(f"{p['doc_id']} p.{p['page']}: no method")
        if p["method"] == "excluded" and not p["reason"]:
            problems.append(f"{p['doc_id']} p.{p['page']}: excluded without reason")
    return problems


def page_report(pages: list[dict]) -> str:
    lines = ["## Pages", "", "| Document | Pages | Text | OCR | Excluded | Mixed (Hindi blocks dropped) | OCR mean conf |",
             "|---|---|---|---|---|---|---|"]
    for d in dict.fromkeys(p["doc_id"] for p in pages):
        ps = [p for p in pages if p["doc_id"] == d]
        c = Counter(p["method"] for p in ps)
        confs = [p["ocr_conf"] for p in ps if p["ocr_conf"] is not None]
        mixed = [p["page"] for p in ps if p["script"] == "mixed"]
        lines.append(f"| {d} | {len(ps)} | {c['text']} | {c['ocr']} | {c['excluded']} | "
                     f"{', '.join(map(str, mixed)) or '–'} | {sum(confs) / len(confs):.3f} |" if confs else
                     f"| {d} | {len(ps)} | {c['text']} | {c['ocr']} | {c['excluded']} | "
                     f"{', '.join(map(str, mixed)) or '–'} | – |")
    lines += ["", "### OCR pages", ""]
    lines += [f"- {p['doc_id']} p.{p['page']}: conf {p['ocr_conf']}" for p in pages if p["method"] == "ocr"]
    lines += ["", "### Excluded pages", ""]
    lines += [f"- {p['doc_id']} p.{p['page']}: {p['reason']}" for p in pages if p["method"] == "excluded"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(prog="claimguard.kb")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--no-ocr", action="store_true")
    b.add_argument("--doc")
    b.add_argument("--no-tag", action="store_true")
    b.add_argument("--no-index", action="store_true")
    b.add_argument("--pages-only", action="store_true")
    sub.add_parser("check")
    a = ap.parse_args()
    from ..config import load_dotenv
    load_dotenv()
    if a.cmd == "check":
        from .clauses import spot_checks
        res = spot_checks()
        for r in res:
            print(("OK  " if r["found"] else "MISS"), r["doc"], r["page"], r["text"][:70], "->", r.get("clause_id"))
        print(f"{sum(r['found'] for r in res)}/{len(res)} found")
        raise SystemExit(0 if all(r["found"] for r in res) else 1)
    pages = build_pages(ocr=not a.no_ocr, only=a.doc)
    problems = page_gates(pages)
    report = ["# Knowledge build report", "", page_report(pages)]
    if not a.pages_only:
        from .clauses import build_clauses, clause_gates, clause_report
        clauses = build_clauses(pages, tag=not a.no_tag)
        problems += clause_gates(clauses)
        report += ["", clause_report(clauses)]
        if not a.no_index:
            from ..retrieval.index import build_index
            n = build_index(clauses)
            report += ["", f"Indexed {n} chunks (BM25 + bge-small vectors)."]
    report += ["", "## Gates", ""] + ([f"- FAIL: {p}" for p in problems] or ["- all passed"])
    (path("build") / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
