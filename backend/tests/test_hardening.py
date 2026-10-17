import time

from fastapi.testclient import TestClient

from claimguard import config
from claimguard.agents.normalise import boxes_for, from_image
from claimguard.agents.pipeline import audit
from claimguard.api import main as api
from claimguard.config import ROOT

from .kbfix import make_kb
from .test_agents import scripted

PACK = ROOT / "data" / "samples" / "packs" / "P1-sparkla-dishwash.png"


def test_image_pipeline_maps_boxes():
    text, boxes, _ = from_image(PACK.read_bytes(), use_vision=False)
    s = text.find("Kills 99.9% germs")
    assert s >= 0
    hit = boxes_for(s, s + len("Kills 99.9% germs"), boxes)
    assert len(hit) == 1 and hit[0][2] > hit[0][0]


def test_long_input_is_capped(tmp_path, monkeypatch):
    make_kb(tmp_path, monkeypatch)
    big = "Kills 99.9% germs. " * 3000
    out = audit(big, "ecommerce", "home", db_url="sqlite://")
    assert len(out.text) == config.settings()["app"]["max_input_chars"]


def test_public_demo_rate_limit(tmp_path, monkeypatch):
    make_kb(tmp_path, monkeypatch)
    monkeypatch.setattr(api.app.state, "db_url", f"sqlite:///{tmp_path / 'r.db'}")
    monkeypatch.setattr(api.app.state, "llm_factory", lambda: scripted([]))
    monkeypatch.setitem(config.settings()["app"], "public_demo", True)
    api._hits.clear()
    c = TestClient(api.app)
    codes = [c.post("/api/preflight", json={"text": "Smells lovely.", "surface": "ecommerce", "category": "home"}).status_code
             for _ in range(22)]
    assert codes[:20] == [200] * 20 and codes[-1] == 429
    api._hits.clear()


def test_image_audit_end_to_end(tmp_path, monkeypatch):
    make_kb(tmp_path, monkeypatch)
    monkeypatch.setattr(api.app.state, "db_url", f"sqlite:///{tmp_path / 'i.db'}")
    monkeypatch.setattr(api.app.state, "llm_factory", lambda: scripted([]))
    monkeypatch.setitem(config.settings()["app"], "public_demo", False)
    monkeypatch.setattr("claimguard.kb.vision.available", lambda: False)
    c = TestClient(api.app)
    aid = c.post("/api/audits", data={"input_type": "image"},
                 files={"file": ("p.png", PACK.read_bytes(), "image/png")}).json()["audit_id"]
    for _ in range(200):
        a = c.get(f"/api/audits/{aid}").json()
        if a["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert a["status"] == "done" and a["image_url"] and any(f["boxes"] for f in a["flags"])
