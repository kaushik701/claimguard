from claimguard.llm.fake import FakeLLM
from claimguard.retrieval import search
from claimguard.retrieval.search import retrieve, rrf

from .kbfix import make_kb


def test_fusion_order():
    assert [c for c, _ in rrf([["a", "b", "c"], ["b", "a", "d"]])][:2] in (["a", "b"], ["b", "a"])
    assert [c for c, _ in rrf([["a", "b"], ["b"]])][0] == "b"


def test_filters_scope(tmp_path, monkeypatch):
    make_kb(tmp_path, monkeypatch)
    home = retrieve("India's favourite health drink", "nutrition_health", "home", "ecommerce")
    assert all(c["doc_id"] != "MF" for c in home)                    # food rule never for home care
    food = retrieve("India's favourite health drink", "nutrition_health", "food", "ecommerce")
    assert food[0]["clause_id"] == "MF-4"
    assert all(c["clause_id"] != "MI-1" for c in retrieve("paid post", "disclosure", "beauty", "ecommerce"))


def test_rerank_not_covered(tmp_path, monkeypatch):
    make_kb(tmp_path, monkeypatch)
    low = FakeLLM(handlers={"reranker": lambda p: {"ranked": [{"clause_id": "MG-1", "score": 1, "why": "tangential"}]},
                            "query_expander": lambda p: {"queries": []}})
    assert retrieve("Eco-friendly formula", "environmental", "home", "ecommerce", llm=low) == []
    (tmp_path / "llm_retrieval_cache.json").unlink(missing_ok=True)
    search._cache.cache_clear()
    hi = FakeLLM(handlers={"reranker": lambda p: {"ranked": [{"clause_id": "MG-1", "score": 3, "why": "direct"}]},
                           "query_expander": lambda p: {"queries": ["environmental claim qualifier"]}})
    got = retrieve("Eco-friendly formula", "environmental", "home", "ecommerce", llm=hi)
    assert [c["clause_id"] for c in got] == ["MG-1"] and got[0]["rerank_score"] == 3
