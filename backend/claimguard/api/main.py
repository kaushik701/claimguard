"""ClaimGuard API (FastAPI). Run: uvicorn claimguard.api.main:app --port 8000  (from backend/)

Routes per docs/API_CONTRACT.md under /api. LLM access is created per request from env keys; tests inject a
FakeLLM via app.state.llm_factory. Audits run in a background thread; progress is streamed with SSE."""
from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import defaultdict, deque
from html import escape
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlmodel import select
from sse_starlette.sse import EventSourceResponse

from ..agents import normalise as nm
from ..agents.pipeline import audit as run_pipeline
from ..config import ROOT, key_status, load_dotenv, path, settings
from ..db import Audit, ChatSession, EvalRun, FlagRow, session
from ..kb.clauses import clauses_by_id, load_store
from ..kb.ingest import page_image, sources
from . import service as svc

load_dotenv()
app = FastAPI(title="ClaimGuard API", version="1.0.0",
              description="Risk indicators for reviewers, not legal advice. Grounded only in five official PDFs.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.state.db_url = None
app.state.llm_factory = None          # tests: lambda: FakeLLM(...)
app.state.last_error = None
SURFACES = Literal["ecommerce", "quick_commerce", "brand_site", "social_post"]
CATEGORIES = Literal["home", "beauty", "personal", "food"]
_hits: dict[str, deque] = defaultdict(deque)


def err(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(HTTPException)
async def http_error(_req, exc: HTTPException):
    return err(exc.status_code, str(exc.detail.get("code") if isinstance(exc.detail, dict) else "error"),
               exc.detail.get("message") if isinstance(exc.detail, dict) else str(exc.detail))


def fail(status: int, code: str, message: str):
    raise HTTPException(status, {"code": code, "message": message})


def rate_limit(request: Request, per_min: int = 20):
    """Per-IP limit in public demo mode (audits, preflight, ask)."""
    if not settings()["app"]["public_demo"]:
        return
    ip = request.client.host if request.client else "?"
    q, now = _hits[ip], time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= per_min:
        fail(429, "rate_limited", "Too many requests from this address. Try again in a minute.")
    q.append(now)


def get_llms():
    """(main LLM, verifier LLM) or (None, None) when no key: the pipeline then uses the rule engine."""
    if app.state.llm_factory:
        x = app.state.llm_factory()
        return x, x
    try:
        from ..llm.client import LLMClient
        x = LLMClient()
        return x, x
    except Exception as e:
        app.state.last_error = str(e)[:200]
        return None, None


# ---------------------------------------------------------------- health
@app.get("/api/health")
def health():
    try:
        st = load_store()
        kb = {"built_at": time.strftime("%Y-%m-%d %H:%M", time.localtime((path("build") / "clauses.json").stat().st_mtime)),
              "docs": len({c["doc_id"] for c in st["clauses"]}), "clauses": len(st["clauses"])}
    except Exception:
        kb = {"built_at": None, "docs": 0, "clauses": 0}
    cfg = settings()["llm"]
    return {"status": "ok", "providers": key_status(), "kb": kb, "public_demo": settings()["app"]["public_demo"],
            "models": {k: v for k, v in cfg.items() if k.endswith("_model")}, "last_error": app.state.last_error}


# ---------------------------------------------------------------- audits
def _run_audit(audit_id: int, text: str, surface: str, category: str, paid: bool):
    db = app.state.db_url
    llm, ver = get_llms()

    def on_step(name, status, ms):
        with session(db) as s:
            a = s.get(Audit, audit_id)
            steps = [x for x in (a.steps or []) if x["name"] != name] + [{"name": name, "status": status, "ms": ms}]
            a.steps, a.status = steps, "running"
            s.add(a)
            s.commit()
    t0 = time.time()
    try:
        out = run_pipeline(text, surface, category, paid, llm=llm, verifier_llm=ver, on_step=on_step, db_url=db)
        if llm is None:
            out.fallback_used, out.fallback_reason = True, "no LLM key configured"
        svc.save_output(db, audit_id, out, llm, t0)
    except Exception as e:
        with session(db) as s:
            a = s.get(Audit, audit_id)
            a.status, a.error = "error", f"{type(e).__name__}: {str(e)[:300]}"
            s.add(a)
            s.commit()


def _input_text(input_type: str, text: Optional[str], file: Optional[UploadFile]) -> tuple[str, list, Optional[str]]:
    if input_type == "text":
        if not text or not text.strip():
            fail(422, "empty_input", "Paste the listing or caption text.")
        return text, [], None
    if file is None:
        fail(422, "missing_file", f"Upload a file for input type '{input_type}'.")
    data = file.file.read()
    try:
        nm.check_upload(input_type, file.filename or "", data)
    except nm.InputError as e:
        fail(422, "bad_upload", str(e))
    if input_type == "html":
        return nm.from_html(data), [], None
    if input_type == "pdf":
        return nm.from_pdf(data), [], None
    txt, boxes, note = nm.from_image(data)
    up = ROOT / "data" / "uploads"
    up.mkdir(parents=True, exist_ok=True)
    f = up / f"{int(time.time() * 1000)}{Path(file.filename or 'x.png').suffix.lower()}"
    f.write_bytes(data)
    return txt, boxes, str(f)


@app.post("/api/audits")
def create_audit(request: Request, input_type: Literal["text", "html", "pdf", "image"] = Form("text"),
                 text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None),
                 surface: SURFACES = Form("ecommerce"), category: CATEGORIES = Form("home"),
                 brand: str = Form(""), paid: bool = Form(False), sample_id: Optional[str] = Form(None)):
    rate_limit(request)
    if settings()["app"]["public_demo"] and input_type != "text" and not sample_id:
        fail(403, "public_demo", "The public demo accepts pasted text and the fictional samples only.")
    body, boxes, img = _input_text(input_type, text, file)
    body = body[: settings()["app"]["max_input_chars"]]
    if not body.strip():
        fail(422, "no_text", "No readable text was found in the input.")
    with session(app.state.db_url) as s:
        a = Audit(input_type=input_type, surface=surface, category=category, brand=brand[:80], paid=paid, text=body,
                  image_path=img, ocr_boxes=[{k: b[k] for k in ("text", "conf", "box", "start", "end")} for b in boxes],
                  status="queued", steps=[{"name": n, "status": "pending", "ms": 0} for n in
                                          ["Reading", "Finding claims", "Finding rules", "Judging", "Checking"]])
        s.add(a)
        s.commit()
        s.refresh(a)
        aid = a.id
    threading.Thread(target=_run_audit, args=(aid, body, surface, category, paid), daemon=True).start()
    return {"audit_id": aid}


@app.get("/api/audits/{audit_id}/events")
async def audit_events(audit_id: int):
    async def gen():
        sent = {}
        for _ in range(1200):                              # up to ~6 minutes
            a = svc.audit_dict(app.state.db_url, audit_id)
            if a is None:
                yield {"event": "error", "data": json.dumps({"message": "audit not found"})}
                return
            for st in a["steps"]:
                key = (st["name"], st["status"])
                if sent.get(st["name"]) != key:
                    sent[st["name"]] = key
                    yield {"event": "step", "data": json.dumps(st)}
            if a["status"] == "done":
                yield {"event": "done", "data": json.dumps({"audit_id": audit_id})}
                return
            if a["status"] == "error":
                yield {"event": "error", "data": json.dumps({"message": a["error"]})}
                return
            await asyncio.sleep(0.3)
    return EventSourceResponse(gen())


@app.get("/api/audits/{audit_id}")
def get_audit(audit_id: int):
    a = svc.audit_dict(app.state.db_url, audit_id)
    if a is None:
        fail(404, "not_found", f"Audit {audit_id} not found.")
    return a


@app.get("/api/audits/{audit_id}/image")
def audit_image(audit_id: int):
    with session(app.state.db_url) as s:
        a = s.get(Audit, audit_id)
        if not a or not a.image_path or not Path(a.image_path).exists():
            fail(404, "not_found", "No image for this audit.")
        return FileResponse(a.image_path)


@app.get("/api/audits")
def list_audits(limit: int = Query(50, ge=1, le=500), brand: Optional[str] = None, surface: Optional[str] = None):
    with session(app.state.db_url) as s:
        q = select(Audit).order_by(Audit.id.desc())
        if brand:
            q = q.where(Audit.brand == brand)
        if surface:
            q = q.where(Audit.surface == surface)
        rows = s.exec(q.limit(limit)).all()
        out = []
        for a in rows:
            flags = s.exec(select(FlagRow).where(FlagRow.audit_id == a.id)).all()
            out.append({"id": a.id, "created_at": a.created_at.isoformat(), "brand": a.brand, "surface": a.surface,
                        "category": a.category, "input_type": a.input_type, "status": a.status,
                        "snippet": a.text[:120], "high": sum(f.risk == "high" for f in flags),
                        "medium": sum(f.risk == "medium" for f in flags), "fallback_used": a.fallback_used})
        return out


@app.get("/api/samples")
def samples():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "data" / "samples").glob("*.json"))]


# ---------------------------------------------------------------- flags / review
class FlagPatch(BaseModel):
    action: Literal["accept", "dismiss", "escalate", "set_risk"]
    risk: Optional[Literal["high", "medium", "low"]] = None
    reason_code: Optional[Literal["wrong_clause", "not_a_claim", "substantiated", "puffery", "wrong_risk", "other"]] = None
    note: Optional[str] = None
    reviewer: Optional[str] = None


@app.patch("/api/flags/{flag_id}")
def patch_flag(flag_id: int, body: FlagPatch):
    if body.action == "set_risk" and not body.risk:
        fail(422, "missing_risk", "set_risk needs a risk.")
    out = svc.apply_feedback(app.state.db_url, flag_id, body.action, body.risk, body.reason_code, body.note,
                             body.reviewer)
    if not out:
        fail(404, "not_found", f"Flag {flag_id} not found.")
    return out


@app.get("/api/flags")
def list_flags(status: Optional[str] = None, risk: Optional[str] = None, claim_type: Optional[str] = None,
               regulator: Optional[str] = None, surface: Optional[str] = None, brand: Optional[str] = None,
               min_conf: Optional[float] = None, max_conf: Optional[float] = None):
    store = clauses_by_id()
    with session(app.state.db_url) as s:
        q = select(FlagRow)
        if status:
            q = q.where(FlagRow.status == status)
        if risk:
            q = q.where(FlagRow.risk == risk)
        out = []
        for f in s.exec(q).all():
            d = svc.flag_dict(s, f, store)
            if claim_type and d["claim"].get("claim_type") != claim_type:
                continue
            if regulator and not any(store.get(c["clause_id"], {}).get("regulator") == regulator for c in d["citations"]):
                continue
            if surface and d["surface"] != surface or brand and d["brand"] != brand:
                continue
            conf = d["confidence"] if d["confidence"] is not None else 1.0
            if (min_conf is not None and conf < min_conf) or (max_conf is not None and conf > max_conf):
                continue
            out.append(d)
        out.sort(key=lambda d: (d["confidence"] if d["confidence"] is not None else 1.0))
        return out


# ---------------------------------------------------------------- pre-flight and copilot
class PreflightIn(BaseModel):
    text: str
    surface: SURFACES = "social_post"
    category: CATEGORIES = "beauty"
    paid: bool = False


@app.post("/api/preflight")
def preflight(request: Request, body: PreflightIn):
    rate_limit(request)
    if not body.text.strip():
        fail(422, "empty_input", "Paste the draft text.")
    llm, ver = get_llms()
    out = run_pipeline(body.text[: settings()["app"]["max_input_chars"]], body.surface, body.category, body.paid,
                       llm=llm, verifier_llm=ver, db_url=app.state.db_url)
    flags = [f.model_dump() for f in out.flags]
    verdict = "revise" if any(f["risk"] == "high" for f in flags) else ("check" if flags else "clear")
    return {"verdict": verdict, "flags": flags, "not_covered": [c.model_dump() for c in out.not_covered],
            "fallback_used": out.fallback_used or llm is None,
            "caveat": "No flags means no rule in the five documents was triggered; it is not clearance."}


class AskIn(BaseModel):
    session_id: Optional[int] = None
    message: str


@app.post("/api/ask")
def ask(request: Request, body: AskIn):
    rate_limit(request)
    from ..agents.copilot import answer
    llm, _ = get_llms()
    if llm is None:
        fail(503, "ai_unavailable", "Ask the Guidelines needs an LLM key (GROQ_API_KEY).")
    with session(app.state.db_url) as s:
        cs = s.get(ChatSession, body.session_id) if body.session_id else None
        if cs is None:
            cs = ChatSession(turns=[])
            s.add(cs)
            s.commit()
            s.refresh(cs)
        history = list(cs.turns or [])
        res = answer(llm, body.message[:2000], history)
        cs.turns = (history + [{"role": "user", "text": body.message[:2000]},
                               {"role": "assistant", "text": res["answer"]}])[-8:]
        s.add(cs)
        s.commit()
        return {"session_id": cs.id, **res}


# ---------------------------------------------------------------- knowledge base
@app.get("/api/kb/documents")
def kb_documents():
    from ..kb.ingest import load_pages
    pages = load_pages()
    cl = load_store()["clauses"]
    out = []
    for s in sources():
        ps = [p for p in pages if p["doc_id"] == s["id"]]
        cs = [c for c in cl if c["doc_id"] == s["id"]]
        confs = [p["ocr_conf"] for p in ps if p["ocr_conf"] is not None]
        out.append({"doc_id": s["id"], "title": s["title"], "regulator": s["regulator"], "source_url": s.get("source_url"),
                    "pages": len(ps), "pages_text": sum(p["method"] == "text" for p in ps),
                    "pages_ocr": sum(p["method"] == "ocr" for p in ps),
                    "pages_excluded": sum(p["method"] == "excluded" for p in ps),
                    "excluded": [{"page": p["page"], "reason": p["reason"]} for p in ps if p["method"] == "excluded"],
                    "clauses": len(cs), "clauses_enabled": sum(c["enabled"] for c in cs),
                    "ocr_mean_conf": round(sum(confs) / len(confs), 3) if confs else None})
    return out


@app.get("/api/kb/clauses")
def kb_clauses(q: Optional[str] = None, doc: Optional[str] = None, tag: Optional[str] = None,
               page: Optional[int] = None, enabled_only: bool = False, offset: int = 0, limit: int = Query(50, le=500)):
    cl = load_store()["clauses"]
    sel = [c for c in cl if (not doc or c["doc_id"] == doc) and (not tag or tag in c["claim_types"])
           and (not page or c["page_start"] <= page <= c["page_end"]) and (not enabled_only or c["enabled"])
           and (not q or q.lower() in f"{c['clause_id']} {c['section_path']} {c['text']}".lower())]
    return {"total": len(sel), "items": sel[offset: offset + limit]}


@app.get("/api/kb/clauses/{clause_id}")
def kb_clause(clause_id: str):
    c = clauses_by_id().get(clause_id)
    if not c:
        fail(404, "not_found", f"Clause {clause_id} not found.")
    from ..learning.stats import clause_stats
    return {**c, "stats": clause_stats(clause_id, app.state.db_url),
            "page_image_url": f"/api/kb/pages/{c['doc_id']}/{c['page_start']}.png"}


class TagsIn(BaseModel):
    claim_types: list[str] = []
    categories: list[str] = []
    surfaces: list[str] = []


@app.patch("/api/kb/clauses/{clause_id}/tags")
def kb_tags(clause_id: str, body: TagsIn):
    from ..kb.tagger import save_override
    store = clauses_by_id()
    if clause_id not in store:
        fail(404, "not_found", f"Clause {clause_id} not found.")
    if settings()["app"]["public_demo"]:
        fail(403, "public_demo", "Tag editing is disabled in the public demo.")
    save_override(clause_id, body.model_dump())
    # apply now to the live store (a rebuild re-applies it)
    data = load_store()
    for c in data["clauses"]:
        if c["clause_id"] == clause_id:
            c.update(body.model_dump(), tag_source="manual")
    (path("build") / "clauses.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    load_store.cache_clear()
    return clauses_by_id()[clause_id]


@app.get("/api/kb/pages/{doc_id}/{page}.png")
def kb_page(doc_id: str, page: int):
    f = page_image(doc_id, page)
    if not f.exists() or doc_id not in {s["id"] for s in sources()}:
        fail(404, "not_found", "Page image not found.")
    return FileResponse(f, media_type="image/png")


@app.get("/api/kb/pdfs/{doc_id}.pdf")
def kb_pdf(doc_id: str):
    src = next((s for s in sources() if s["id"] == doc_id), None)
    if not src:
        fail(404, "not_found", "Unknown document.")
    return FileResponse(ROOT / "knowledge" / "pdfs" / src["file"], media_type="application/pdf")


# ---------------------------------------------------------------- portfolio, eval, reports
@app.get("/api/portfolio")
def portfolio():
    from .portfolio import build
    return build(app.state.db_url)


@app.get("/api/eval/runs")
def eval_runs():
    with session(app.state.db_url) as s:
        rows = s.exec(select(EvalRun).order_by(EvalRun.id.desc())).all()
        return [{"id": r.id, "created_at": r.created_at.isoformat(), "set_name": r.set_name, "config": r.config_json,
                 "metrics": {k: v for k, v in r.metrics_json.items() if not isinstance(v, (list, dict))},
                 "report_path": r.report_path} for r in rows]


@app.get("/api/eval/runs/{run_id}")
def eval_run(run_id: int):
    with session(app.state.db_url) as s:
        r = s.get(EvalRun, run_id)
        if not r:
            fail(404, "not_found", "Eval run not found.")
        return {"id": r.id, "created_at": r.created_at.isoformat(), "set_name": r.set_name, "config": r.config_json,
                "metrics": r.metrics_json, "report_path": r.report_path}


@app.get("/api/reports/{audit_id}.html", response_class=HTMLResponse)
def report(audit_id: int):
    a = svc.audit_dict(app.state.db_url, audit_id)
    if a is None:
        fail(404, "not_found", "Audit not found.")
    e = escape
    flags = "".join(
        f"<div class='flag {e(f['risk'])}'><p><b>{e(f['risk'].upper())}</b> · {e(f['claim'].get('claim_type', ''))} · "
        f"status: {e(f['status'])}</p><h3>{e(f['claim'].get('text', ''))}</h3><p><b>Why:</b> {e(f['reason'])}</p>"
        + "".join(f"<blockquote>“{e(c['quote'])}”</blockquote><p class='src'>{e(c['doc_title'])} · "
                  f"{e(c['section_path'])} · page {c['page']}{' · OCR, check against PDF' if c['source'] == 'ocr' else ''}</p>"
                  for c in f["citations"])
        + (f"<p><b>Suggested:</b> {e(f['rewrite'])}</p>" if f["rewrite"] else "") + "</div>" for f in a["flags"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ClaimGuard audit {a['id']}</title><style>body{{font-family:'IBM Plex Sans',system-ui,sans-serif;color:#14171F;max-width:860px;margin:24px auto;padding:0 16px;line-height:1.5}}
h1{{color:#1F3A93}}.flag{{border:1px solid #DADDE3;border-left:6px solid #D92D20;border-radius:8px;padding:4px 14px;margin:12px 0;break-inside:avoid}}
.flag.medium{{border-left-color:#B54708}}blockquote{{font-family:'Source Serif 4',Georgia,serif;background:#FAFAFB;border-left:3px solid #1F3A93;margin:6px 0;padding:4px 12px}}
.src,.fine{{font-size:12px;color:#545B69}}pre{{white-space:pre-wrap;background:#F5F6F8;padding:10px;border-radius:6px}}</style></head><body>
<h1>ClaimGuard audit #{a['id']}</h1><p class="fine">{e(a['brand'] or '–')} · {e(a['surface'])} · {e(a['category'])} · {e(a['created_at'][:16])}</p>
<p class="fine">Risk indicators for reviewers, not legal advice. Not affiliated with or endorsed by any brand owner.</p>
<p>Claims {a['stats']['claims']} · High {a['stats']['high']} · Medium {a['stats']['medium']} · Not covered {a['stats']['not_covered']}</p>
<h2>Input</h2><pre>{e(a['text'])}</pre><h2>Flags</h2>{flags or '<p>No medium or high-risk claims.</p>'}</body></html>"""


DIST = ROOT / "frontend" / "dist"


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    """Serve the built React app (frontend/dist) on the same port; unknown paths get index.html."""
    if full_path.startswith("api/"):
        fail(404, "not_found", "Unknown API route.")
    f = (DIST / full_path).resolve()
    if full_path and f.is_file() and DIST.resolve() in f.parents:
        return FileResponse(f)
    if (DIST / "index.html").exists():
        return FileResponse(DIST / "index.html")
    fail(404, "no_frontend", "Frontend not built: run `npm run build` in frontend/.")
