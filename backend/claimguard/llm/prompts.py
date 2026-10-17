"""Prompt loader: fills {placeholders} in prompts/<name>.md. Untrusted text is neutralised so it cannot close the
<<<INPUT ... INPUT>>> fence; every placeholder must be supplied (no silent blanks)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).parent / "prompts"
_PH = re.compile(r"\{([a-z_]+)\}")
UNTRUSTED = {"text", "clause_text", "claim", "question"}


@lru_cache(maxsize=None)
def template(name: str) -> str:
    return (DIR / f"{name}.md").read_text(encoding="utf-8")


def placeholders(name: str) -> set[str]:
    return set(_PH.findall(template(name)))


def neutralise(s: str) -> str:
    """Untrusted data can't forge the fence markers or smuggle new ones."""
    return str(s).replace("<<<", "‹‹‹").replace(">>>", "›››").replace("INPUT>>>", "INPUT›››")


def render(name: str, **values) -> str:
    need = placeholders(name)
    missing = need - set(values)
    if missing:
        raise KeyError(f"prompt {name}: missing {sorted(missing)}")
    out = template(name)
    for k in need:
        v = values[k]
        v = neutralise(v) if k in UNTRUSTED else str(v)
        out = out.replace("{" + k + "}", v)
    return out
