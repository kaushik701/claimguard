"""Structure-aware clause segmentation (ported and extended from ClaimGuard v1, measured on these PDFs).

- Page-number lines, running headers (lines repeated on many pages) and bold text printed several times over
  are removed first.
- A clause starts at a numbered heading (1.1, 4.2, 6(10), 1), Rule 6, Regulation 4) followed by words, after a
  capitals section title, or at a titled line with an em dash ("Adequate disclosures — ...", used by the scanned
  CCPA paper whose OCR loses small margin numbers). Years / table values (2019, 0.75, 100) are not clause numbers.
- Short list items are joined to the clause before them, so no text is dropped.
- IDs: <DOC>-<number>; a number that repeats in a later guideline gets its page (<DOC>-1-p31); unnumbered text
  after a title is <DOC>-p<page>. Numbers are never guessed.
"""
from __future__ import annotations

import hashlib
import re
from bisect import bisect_right

_PAGE_NUMBER = re.compile(r"^[ \t]*\d{1,3}[ \t]*$\n?", re.M)
_HEADING = re.compile(r"^\s*((?:Rule|Regulation|Guideline)\s+)?(\d+(?:\.\d+)*(?:\(\d+\))?)[.)]?\s+"
                      r"(?!(?:g|mg|mcg|ml|kg|kcal|kj|l|per|cm|mm|IU|times)\b)(?=[A-Za-z(“\"‘'])", re.M)
_TITLED = re.compile(r"^[ \t]*[A-Z][A-Za-z ,/&()'’-]{3,70}?[ \t]+[—–-][ \t]*(?=[A-Z(])", re.M)
_CAPS_LINE = re.compile(r"^[ \t]*(?=[^a-z\n]*[A-Z]{3})[^a-z\n]{10,}$", re.M)
_GENERIC_TITLE = re.compile(r"^(GUIDELINES?|DEFINITIONS?|PREAMBLE|CONTINUED|NOTES?|EXAMPLES?)\W*$")
MIN_LEN = 60


def _collapse_repeats(text: str) -> str:
    out: list[str] = []
    for line in text.split("\n"):
        if out and line.strip() and line.strip() == out[-1].strip():
            continue
        out.append(line)
    return "\n".join(out)


def clean_pages(texts: list[str]) -> list[str]:
    """Strip page numbers, repeated bold lines and running headers/footers: a line in the first or last 3 lines
    of >= 30% of >= 4 text pages (table phrases repeated mid-page, like 'Not more than', are kept)."""
    out = [_collapse_repeats(_PAGE_NUMBER.sub("", t)) for t in texts]
    with_text = sum(bool(t.strip()) for t in out)
    edges = lambda t: [x.strip() for x in t.split("\n") if x.strip()]  # noqa: E731
    counts: dict[str, int] = {}
    for t in out:
        ls = edges(t)
        for ln in {x for x in ls[:3] + ls[-3:] if len(x) >= 8}:
            counts[ln] = counts.get(ln, 0) + 1
    header = {ln for ln, n in counts.items() if with_text >= 4 and n >= max(3, 0.3 * with_text)}

    def strip(t: str) -> str:
        ls = t.split("\n")
        idx = [i for i, x in enumerate(ls) if x.strip()]
        edge = set(idx[:3] + idx[-3:])
        return "\n".join(x for i, x in enumerate(ls) if not (i in edge and x.strip() in header))
    return [strip(t) for t in out]


def _sections(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for m in _CAPS_LINE.finditer(text):
        title = re.sub(r"\s+", " ", m.group(0)).strip()
        if out and m.start() <= out[-1][1] + 1:
            out[-1] = (out[-1][0], m.end(), f"{out[-1][2]} {title}")
        elif out and _GENERIC_TITLE.match(title):
            out.append((m.start(), m.end(), f"{out[-1][2].split(' / ')[0]} / {title}"))
        else:
            out.append((m.start(), m.end(), title))
    return out


def _plausible(ref: str) -> bool:
    lead = re.match(r"\d+", ref).group(0)
    return not lead.startswith("0") and int(lead) < 100


def split(text: str) -> list[tuple[str, str, int, int, str]]:
    """(number, body, start, end, section_title) over the whole document text."""
    sections = _sections(text)
    numbered = [(m.start(), m.end(), m.group(2), m.start(2)) for m in _HEADING.finditer(text)
                if _plausible(m.group(2)) and not any(s <= m.start() < e for s, e, _ in sections)]
    ends = {e for _, e, _, _ in numbered}
    titled = [(m.start(), m.start(), "", m.start()) for m in _TITLED.finditer(text)
              if m.start() not in ends and not text[max(0, m.start() - 12):m.start()].strip().rstrip(".)").isdigit()
              and not any(s <= m.start() < e for s, e, _ in sections)]
    bounds = sorted(numbered + titled + [(s, e, "", s) for s, e, _ in sections])
    sec_starts = [s for s, _, _ in sections]
    out: list[tuple[str, str, int, int, str]] = []
    for i, (start, end, ref, pos) in enumerate(bounds):
        stop = bounds[i + 1][0] if i + 1 < len(bounds) else len(text)
        body = re.sub(r"\s+", " ", text[end:stop]).strip()
        k = bisect_right(sec_starts, start) - 1
        section = sections[k][2] if k >= 0 else ""
        if len(body) >= MIN_LEN:
            out.append((ref, body, pos, stop, section))
        elif ref and out and body:
            r, prev, p, _, sec = out[-1]
            out[-1] = (r, f"{prev} {text[start:end].strip()} {body}", p, stop, sec)
    return out


def segment_doc(src: dict, pages: list[dict]) -> list[dict]:
    """Clauses for one document from its page records (only text/ocr pages; excluded pages contribute nothing)."""
    pages = sorted(pages, key=lambda p: p["page"])
    usable = [p for p in pages if p["method"] in ("text", "ocr")]
    texts = clean_pages([p["text"] for p in usable])
    starts, doc = [], ""
    for t in texts:
        starts.append(len(doc))
        doc += t + "\n"
    conf = {p["page"]: p["ocr_conf"] for p in usable}
    method = {p["page"]: p["method"] for p in usable}
    page_of = lambda pos: usable[max(0, bisect_right(starts, pos) - 1)]["page"]  # noqa: E731
    used, out = set(), []
    for ref, body, pos, stop, section in split(doc):
        p0, p1 = page_of(pos), page_of(max(pos, stop - 1))
        cid = f"{src['id']}-{ref}" if ref else f"{src['id']}-p{p0}"
        if cid in used:
            base = f"{src['id']}-{ref}-p{p0}" if ref else f"{src['id']}-p{p0}"
            cid, n = base, 2
            while cid in used:
                cid, n = f"{base}-{n}", n + 1
        used.add(cid)
        span = range(p0, p1 + 1)
        ocr_pages = [conf[p] for p in span if method.get(p) == "ocr" and conf.get(p) is not None]
        lead = body.split(" — ")[0] if " — " in body[:90] else ""
        title = section.title() if section else ""
        out.append({
            "clause_id": cid, "doc_id": src["id"], "regulator": src["regulator"], "doc_title": src["title"],
            "section_path": " > ".join(x for x in (title, ref or lead) if x),
            "number": ref or None, "title": (lead or body[:80]), "text": body,
            "page_start": p0, "page_end": p1, "source": "ocr" if ocr_pages else "text",
            "ocr_conf": round(sum(ocr_pages) / len(ocr_pages), 3) if ocr_pages else None,
            "hash": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16], "duplicate_of": None,
        })
    return out


def norm(s: str) -> str:
    """Whitespace/quote/case-normalised text for verbatim checks."""
    s = s.translate(_NORM_MAP)
    return re.sub(r"\s+", " ", s).strip().lower()


# quotes, dashes and hyphen variants (models often emit U+2011 non-breaking hyphens), odd spaces
_NORM_MAP = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "‐": "-", "‑": "-",
                           "‒": "-", "−": "-", " ": " ", " ": " ", " ": " "})


def dedupe(clauses: list[dict]) -> None:
    """Same text in two documents: keep both IDs, mark the later one `duplicate_of` the first."""
    first: dict[str, str] = {}
    for c in clauses:
        k = re.sub(r"\W+", "", c["text"].lower())
        if k in first:
            c["duplicate_of"] = first[k]
        else:
            first[k] = c["clause_id"]
