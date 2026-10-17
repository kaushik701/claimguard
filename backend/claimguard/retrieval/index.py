"""Chunks + BM25 (pickled) + dense vectors (fastembed bge-small, LanceDB on disk)."""
from __future__ import annotations

import pickle
import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from ..config import path, settings

_TOKEN = re.compile(r"[a-z0-9%]+")
MAX_CHARS = 1400  # ~350 tokens


def tokenize(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


def chunk(c: dict) -> list[dict]:
    head = f"{c['section_path']}. " if c["section_path"] else ""
    if len(c["text"]) <= MAX_CHARS:
        parts = [c["text"]]
    else:
        sents, parts, cur = re.split(r"(?<=[.;:])\s+", c["text"]), [], ""
        for s in sents:
            if cur and len(cur) + len(s) > MAX_CHARS:
                parts.append(cur)
                cur = ""
            cur = f"{cur} {s}".strip()
        if cur:
            parts.append(cur)
    return [{"chunk_id": f"{c['clause_id']}#{i}", "clause_id": c["clause_id"], "text": head + p}
            for i, p in enumerate(parts)]


@lru_cache(maxsize=1)
def embedder():
    from fastembed import TextEmbedding
    import os
    return TextEmbedding(settings()["retrieval"]["embedding_model"], cache_dir=os.getenv("FASTEMBED_CACHE_PATH"))


def embed(texts: list[str]) -> list[list[float]]:
    return [list(map(float, v)) for v in embedder().embed(texts)]


def build_index(clauses: list[dict], dense: bool = True) -> int:
    chunks = [ch for c in clauses if c.get("enabled", True) for ch in chunk(c)]
    out = path("build")
    with open(out / "bm25.pkl", "wb") as f:
        pickle.dump({"chunks": chunks, "bm25": BM25Okapi([tokenize(c["text"]) for c in chunks])}, f)
    if dense:
        import lancedb
        db = lancedb.connect(str(out / "lancedb"))
        vecs = embed([c["text"] for c in chunks])
        db.create_table("chunks", data=[{**c, "vector": v} for c, v in zip(chunks, vecs)], mode="overwrite")
    for f in (load_bm25, dense_table):
        getattr(f, "cache_clear", lambda: None)()
    return len(chunks)


@lru_cache(maxsize=1)
def load_bm25() -> dict:
    with open(path("build") / "bm25.pkl", "rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def dense_table():
    import lancedb
    return lancedb.connect(str(path("build") / "lancedb")).open_table("chunks")
