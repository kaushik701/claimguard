import pytest

from claimguard.config import ROOT
from claimguard.kb.segment import clean_pages, split
from claimguard.kb.xref import cross_refs, definitions

BUILT = (ROOT / "knowledge/build/clauses.json").exists()


def test_split_numbers_titles_and_table_values():
    text = ("CHAPTER - I MADE-UP HONESTY\n1.1 Claims must be truthful and capable of substantiation by made-up tests.\n"
            "1.2 Research claims must name the source and the date of the made-up study.\n"
            "2. Fat\nLow\nNot more than 3 g of fat per 100 g for solids or\n1.5 g of fat per 100ml for liquids.\n"
            "Adequate disclosures — Any person making a made-up claim must disclose material information.\n")
    got = split(text)
    assert [r for r, *_ in got] == ["1.1", "1.2", "2", ""]
    assert "1.5 g of fat per 100ml" in got[2][1]                    # table value is not a clause number
    assert got[0][4] == "CHAPTER - I MADE-UP HONESTY" and got[3][1].startswith("Adequate disclosures")


def test_running_headers_removed_table_phrases_kept():
    pages = [f"MADE-UP GAZETTE EXTRA\nBody {i}\nline a\nNot more than 1 g\nline b\nline c\nline d\nfooter {i}"
             for i in range(6)]
    out = clean_pages(pages)
    assert all("MADE-UP GAZETTE EXTRA" not in p for p in out) and all("Not more than 1 g" in p for p in out)


def test_definitions_and_xrefs():
    cs = [{"clause_id": "D-2", "doc_id": "D", "number": "2", "text": '"health claim" means any made-up statement.'},
          {"clause_id": "D-4", "doc_id": "D", "number": "4", "text": "Claims as per regulation 2 must be truthful."}]
    assert definitions(cs)["health claim"]["clause_id"] == "D-2"
    assert cross_refs(cs) == [("D-4", "D-2")]


@pytest.mark.skipif(not BUILT, reason="run python -m claimguard.kb build first")
def test_real_store_segments_and_spot_checks():
    from claimguard.kb.clauses import clause_gates, load_store, spot_checks
    load_store.cache_clear()
    cs = load_store()["clauses"]
    ids = {c["clause_id"]: c for c in cs}
    assert ids["ASCI-1.1"]["page_start"] == 18 and ids["ASCI-1.2"]["page_start"] == 18     # ASCI Code ch. I
    assert ids["FSSAI-4"]["text"].startswith("General principles")                          # FSSAI Regulation 4
    assert all(s["found"] for s in spot_checks(cs))
    assert clause_gates(cs) == []


def test_tag_overrides_survive_rebuild(tmp_path, monkeypatch):
    from claimguard.kb import tagger
    (tmp_path / "tags.yaml").write_text("X-1: {claim_types: [comparative], enabled: false}\n")
    (tmp_path / "scope.yaml").write_text("rules: []\n")
    monkeypatch.setattr(tagger, "OVERRIDES", tmp_path)
    monkeypatch.setattr(tagger, "CACHE", tmp_path / "none.json")
    c = {"clause_id": "X-1", "doc_id": "X", "doc_title": "Made-up", "section_path": "", "text": "eco-friendly green",
         "hash": "h"}
    tagger.apply_tags([c], [{"id": "X"}])
    assert c["claim_types"] == ["comparative"] and c["enabled"] is False and c["tag_source"] == "manual"
