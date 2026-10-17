import pymupdf
import pytest

from claimguard.config import ROOT
from claimguard.kb import ocr
from claimguard.kb.script_detect import classify, legacy_line

FSSAI = ROOT / "knowledge" / "pdfs" / "FSSAI_Advertising_Claims_Regulations_2018.pdf"


def test_script_detect_on_fssai_pages():
    doc = pymupdf.open(FSSAI)
    assert classify(doc[4].get_text()) == "hi_legacy"      # p.5 Hindi (broken Devanagari)
    assert classify(doc[20].get_text()) == "en"            # p.21 English


def test_legacy_lines_dropped_english_kept():
    for bad in ["Hkkx IIIµ[k.M 4º", "vlk/kj.k", "jftLVªh laö Mhö ,yö&33004@99", "Hkkjr dk jkti=k % vlk/kj.k"]:
        assert legacy_line(bad), bad
    for ok in ["“Act” means the Food Safety and Standards Act, 2006 (34 of 2006);", "(a)", "19",
               "PART III— Section 4", "Claims must be truthful, unambiguous, meaningful."]:
        assert not legacy_line(ok), ok


def test_ocr_adapter_reads_known_text():
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=120)
    page.insert_text((20, 60), "Made-up rule: claims need proof", fontsize=20)
    lines = ocr.ocr_png(page.get_pixmap(dpi=150).tobytes("png"), scale=150 / 72)
    text = " ".join(x["text"] for x in lines)
    assert "claims need proof" in text and all(0 <= x["conf"] <= 1 for x in lines)
    assert lines[0]["box"][0] < 200                            # box back in PDF points


@pytest.mark.skipif(not (ROOT / "knowledge/build/pages.parquet").exists(), reason="run kb build first")
def test_build_accounts_every_page():
    from claimguard.kb.build import page_gates
    from claimguard.kb.ingest import load_pages
    pages = load_pages()
    assert len(pages) == 141 and page_gates(pages) == []
    fssai = {p["page"]: p for p in pages if p["doc_id"] == "FSSAI"}
    assert all(fssai[i]["method"] == "excluded" or "Hkkx" not in fssai[i]["text"] for i in fssai)
    assert sum(p["method"] == "ocr" for p in pages if p["doc_id"] == "CCPA-GW") == 6


def test_vision_parse_variants_and_reconcile():
    from claimguard.kb.vision import parse, reconcile
    a = parse('{"blocks": [{"text": "Kills 99.9% germs", "position": "top"}]}')
    b = parse('[{"bbox_2d": [1, 2, 3, 4], "text_content": "Kills 99.9% germs"}]')
    assert a.blocks[0].text == b.blocks[0].text == "Kills 99.9% germs"
    r = reconcile([{"text": "Kills 99.9% germs"}, {"text": "Made-up misread"}], b)
    assert [x["vision_agrees"] for x in r] == [True, False]
