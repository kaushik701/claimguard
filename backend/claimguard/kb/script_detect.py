"""Script / legacy-font detection for text blocks.

Measured on FSSAI (17 Oct 2026): the Hindi pages extract as *broken* Devanagari (Unicode letters in the wrong
order plus control characters) and a few lines of Latin gibberish ("ubZ fnYyh"); page 19 mixes Hindi and the
start of the English text. So we classify each text block, not whole pages:
  en         - mostly English words (wordfreq zipf > 2)
  hi_legacy  - Devanagari share > 30% of letters, or Latin tokens that are mostly non-words with legacy bigrams
"""
from __future__ import annotations

import re

from wordfreq import zipf_frequency

_DEVA = re.compile(r"[ऀ-ॿ]")
_LETTER = re.compile(r"[A-Za-zऀ-ॿ]")
_TOKEN = re.compile(r"[A-Za-z]{2,}")
LEGACY_BIGRAMS = ("kk", "Hk", "µ", "[k", "ç", "Z", "Yy", "fn")


def english_ratio(text: str) -> float:
    toks = _TOKEN.findall(text)
    if not toks:
        return 0.0
    return sum(zipf_frequency(t.lower(), "en") > 2 for t in toks) / len(toks)


def classify(text: str) -> str:
    letters = len(_LETTER.findall(text))
    if letters < 3:
        return "en"  # numbers / punctuation only: harmless, keep with its neighbours
    if len(_DEVA.findall(text)) > 0.3 * letters:
        return "hi_legacy"
    toks = _TOKEN.findall(text)
    if len(toks) >= 3 and english_ratio(text) < 0.35 and sum(text.count(b) for b in LEGACY_BIGRAMS) >= 2:
        return "hi_legacy"
    return "en"


_STRONG = re.compile(r"[µºª¹öç]")                 # glyphs the legacy font maps to; not used in English text
_WEAK = re.compile(r"\w\[\w|\w/\w|kk|Hk")


def legacy_line(line: str) -> bool:
    """A Latin-gibberish line from a legacy Hindi font (e.g. 'Hkkx IIIµ[k.M 4º', 'vlk/kj.k'): non-English
    words plus legacy glyphs. English lines, numbers and clause markers pass."""
    if not _TOKEN.findall(line):
        return False
    ratio = english_ratio(line)
    if _STRONG.search(line):
        return ratio < 0.8
    return bool(_WEAK.search(line)) and ratio <= 0.5


def page_script(block_scripts: list[str]) -> str:
    s = set(block_scripts)
    if not s:
        return "image_only"
    if s == {"en"}:
        return "en"
    if s == {"hi_legacy"}:
        return "hi_legacy"
    return "mixed"
