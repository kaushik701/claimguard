import json
import time

import pytest
from fastapi.testclient import TestClient

from claimguard import config
from claimguard.api import main as api
from claimguard.db import _ENGINES
from claimguard.llm.fake import FakeLLM

from .kbfix import make_kb
from .test_agents import scripted


@pytest.fixture
def client(tmp_path, monkeypatch):
    make_kb(tmp_path, monkeypatch)
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(api.app.state, "db_url", url)
    monkeypatch.setattr(api.app.state, "llm_factory", lambda: scripted([]))
    monkeypatch.setitem(config.settings()["app"], "public_demo", False)
    yield TestClient(api.app)
    _ENGINES.pop(url, None)


def wait(c, aid):
    for _ in range(100):
        a = c.get(f"/api/audits/{aid}").json()
        if a["status"] in ("done", "error"):
            return a
        time.sleep(0.05)
    raise AssertionError("audit did not finish")


def test_health(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["kb"]["clauses"] == 6


def test_audit_flow_review_and_report(client):
    aid = client.post("/api/audits", data={"input_type": "text", "text": "Kills 99.9% germs. Smells lovely.",
                                           "surface": "ecommerce", "category": "home"}).json()["audit_id"]
    a = wait(client, aid)
    assert a["status"] == "done" and a["flags"] and a["flags"][0]["citations"][0]["quote"]
    assert {s["name"] for s in a["steps"]} >= {"Reading", "Finding claims", "Finding rules", "Judging", "Checking"}
    fid = a["flags"][0]["id"]
    r = client.patch(f"/api/flags/{fid}", json={"action": "dismiss", "reason_code": "substantiated", "note": "lab file"})
    assert r.json()["status"] == "dismissed"
    assert client.patch(f"/api/flags/{fid}", json={"action": "set_risk"}).status_code == 422
    assert client.get("/api/flags?status=dismissed").json()[0]["id"] == fid
    html = client.get(f"/api/reports/{aid}.html").text
    assert "not legal advice" in html and "<script" not in html
    ev = client.get(f"/api/audits/{aid}/events").text
    assert "event: done" in ev


def test_input_validation_and_public_demo(client, monkeypatch):
    assert client.post("/api/audits", data={"input_type": "text", "text": "  "}).status_code == 422
    r = client.post("/api/audits", data={"input_type": "pdf"}, files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 422 and "PDF" in r.json()["error"]["message"]
    monkeypatch.setitem(config.settings()["app"], "public_demo", True)
    r = client.post("/api/audits", data={"input_type": "html"}, files={"file": ("x.html", b"<p>x</p>", "text/html")})
    assert r.status_code == 403


def test_html_upload_text(client):
    page = b"<html><body><h1>Made-up soap</h1><p>Kills 99.9% germs.</p><script>alert(1)</script></body></html>"
    aid = client.post("/api/audits", data={"input_type": "html"}, files={"file": ("p.html", page, "text/html")}).json()["audit_id"]
    a = wait(client, aid)
    assert "Kills 99.9% germs" in a["text"] and "alert(1)" not in a["text"]


def test_preflight_verdicts(client):
    r = client.post("/api/preflight", json={"text": "Kills 99.9% germs.", "surface": "ecommerce", "category": "home"}).json()
    assert r["verdict"] == "revise" and "not clearance" in r["caveat"]
    r = client.post("/api/preflight", json={"text": "Store in a cool, dry place.", "surface": "ecommerce",
                                            "category": "home"}).json()
    assert r["verdict"] == "clear"


def test_kb_routes(client):
    c = client.get("/api/kb/clauses?q=health drink").json()
    assert c["total"] == 1 and c["items"][0]["clause_id"] == "MF-4"
    assert client.get("/api/kb/clauses/MF-4").json()["stats"]["used_in"] == 0
    assert client.get("/api/kb/clauses/NOPE").status_code == 404


def test_contract_routes_exist():
    paths = set(api.app.openapi()["paths"])
    for p in ["/api/health", "/api/audits", "/api/audits/{audit_id}", "/api/audits/{audit_id}/events", "/api/flags",
              "/api/flags/{flag_id}", "/api/preflight", "/api/ask", "/api/kb/documents", "/api/kb/clauses",
              "/api/kb/clauses/{clause_id}", "/api/kb/clauses/{clause_id}/tags", "/api/kb/pages/{doc_id}/{page}.png",
              "/api/portfolio", "/api/eval/runs", "/api/eval/runs/{run_id}", "/api/reports/{audit_id}.html"]:
        assert p in paths, p


def test_ask_refuses_out_of_scope(client, monkeypatch):
    llm = FakeLLM(handlers={"reranker": lambda p: {"ranked": [{"clause_id": "MC-1.1", "score": 0, "why": "no"}]},
                            "query_expander": lambda p: {"queries": []}})
    monkeypatch.setattr(api.app.state, "llm_factory", lambda: llm)
    r = client.post("/api/ask", json={"message": "What is the GST rate on made-up shampoo?"}).json()
    assert r["covered"] is False and "don't address" in r["answer"] and r["citations"] == []


def test_ask_citations_verbatim(client, monkeypatch):
    def ans(p):
        return {"answer": "Claims need substantiation [1]. They must be true [2].", "covered": True, "citations": [
            {"n": 1, "clause_id": "MC-1.1", "quote": "must be capable of substantiation by the advertiser"},
            {"n": 2, "clause_id": "MC-1.1", "quote": "a sentence that is not in the clause at all"}]}
    llm = FakeLLM(handlers={"reranker": lambda p: {"ranked": [{"clause_id": "MC-1.1", "score": 3, "why": ""}]},
                            "query_expander": lambda p: {"queries": []}, "copilot_answer": ans})
    monkeypatch.setattr(api.app.state, "llm_factory", lambda: llm)
    r = client.post("/api/ask", json={"message": "Do performance claims need proof?"}).json()
    assert r["covered"] and [c["n"] for c in r["citations"]] == [1]            # unverifiable citation removed


def test_feedback_changes_memory(client, tmp_path):
    from claimguard.learning.memory import examples_text
    aid = client.post("/api/audits", data={"input_type": "text", "text": "Kills 99.9% germs."}).json()["audit_id"]
    a = wait(client, aid)
    client.patch(f"/api/flags/{a['flags'][0]['id']}", json={"action": "dismiss", "reason_code": "puffery"})
    ex = examples_text(["Kills 99.9% of germs."], db_url=api.app.state.db_url)
    assert "previously judged NOT risky" in ex and "puffery" in ex


def test_holdout_never_in_memory():
    from claimguard.learning.memory import holdout_texts, is_holdout
    h = next(iter(holdout_texts()))
    assert is_holdout(h) and not is_holdout("A completely made-up sentence about soap bubbles.")


def test_calibration_monotonic():
    from sklearn.isotonic import IsotonicRegression
    from claimguard.agents.calibrate import bins
    xs = [0.1, 0.3, 0.5, 0.7, 0.9] * 30
    ys = [0, 0, 1, 1, 1] * 30
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(xs, ys)
    pred = iso.predict([0.1, 0.5, 0.9])
    assert list(pred) == sorted(pred)
    assert bins(list(zip(xs, ys)))[0]["observed"] == 0


def test_eval_smoke(tmp_path, monkeypatch):
    from claimguard.eval import run as ev
    from .kbfix import make_kb as mk
    mk(tmp_path, monkeypatch)
    monkeypatch.setattr(ev, "REPORTS", tmp_path)
    items = [{"id": "x1", "text": "Kills 99.9% germs.", "claim_type": "efficacy", "risk": "high", "category": "home"},
             {"id": "x2", "text": "Store in a cool place.", "claim_type": "none", "risk": "none", "category": "home"}]
    m = ev.run("holdout", "rules", db_url=f"sqlite:///{tmp_path / 'e.db'}", items=items)
    assert m["high_risk_recall"] == 1.0 and m["non_claim_fp_rate"] == 0.0 and list(tmp_path.glob("*.md"))
    assert json.loads(next(tmp_path.glob("eval_*.json")).read_text())["n_items"] == 2
