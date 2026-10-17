"""Ask the Guidelines: standalone question (P10) -> hybrid retrieval (no claim-type filter) -> rerank -> answer
(P9) -> code check that every citation quote is verbatim in its clause -> refusal when coverage is weak."""
from __future__ import annotations

from ..config import settings
from ..kb.clauses import clauses_by_id
from ..kb.segment import norm
from ..llm.prompts import neutralise, render, template
from ..llm.schemas import CopilotOut, QuestionOut
from ..retrieval.search import retrieve

REFUSAL = "The guideline documents in ClaimGuard don't address this."


def standalone(llm, history: list[dict], message: str) -> str:
    if not history:
        return message
    conv = "\n".join(f"{t['role']}: {t['text']}" for t in history[-8:])
    prompt = template("question_rewriter") + "\n\n<<<INPUT\n" + neutralise(conv + f"\nuser: {message}") + "\nINPUT>>>"
    try:
        return llm.json("question_rewriter", prompt, QuestionOut, step="copilot").question or message
    except Exception:
        return message


def answer(llm, message: str, history: list[dict] | None = None) -> dict:
    q = standalone(llm, history or [], message)
    hits = retrieve(q, None, None, None, llm=llm, k=6)
    min_score = settings()["thresholds"]["copilot_min_score"]
    if not hits or (hits[0].get("rerank_score") is not None and hits[0]["rerank_score"] < min_score):
        return {"question": q, "answer": REFUSAL, "citations": [], "covered": False}
    excerpts = "\n\n".join(f"[{i}] {h['clause_id']} ({h['doc_title']}, {h['section_path']}, page {h['page_start']}):\n"
                           f"{h['text'][:1500]}" for i, h in enumerate(hits, 1))
    out = llm.json("copilot_answer", render("copilot_answer", numbered_excerpts_with_doc_page=excerpts, question=q),
                   CopilotOut, step="copilot")
    store, by_n = clauses_by_id(), {i: h for i, h in enumerate(hits, 1)}
    cits = []
    for c in out.citations:
        h = by_n.get(c.n)
        cid = h["clause_id"] if h else c.clause_id
        cl = store.get(cid)
        if cl and len(norm(c.quote)) >= 12 and norm(c.quote) in norm(cl["text"]):
            cits.append({"n": c.n, "clause_id": cid, "doc": cl["doc_title"], "doc_id": cl["doc_id"],
                         "page": cl["page_start"], "quote": c.quote, "ocr_conf": cl.get("ocr_conf")})
    if not out.covered or not cits:
        return {"question": q, "answer": REFUSAL, "citations": [], "covered": False}
    return {"question": q, "answer": out.answer, "citations": cits, "covered": True}
