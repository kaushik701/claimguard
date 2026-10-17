"""One OpenAI-compatible client for Groq / Gemini / OpenAI with validation, retries and provider fallback.

json(name, prompt, schema, step) -> validated Pydantic object.
- Invalid JSON / schema: retry up to max_retries, feeding the error back ONLY after a validation error.
- 429 / timeout / connection drop: wait as long as the provider asks (max 60 s), retry once, then switch to the
  fallback provider for the rest of the run (usage.fallbacks += 1). No fallback key -> LLMError (stop cleanly).
- Every call is recorded in `calls` (prompt name, sha256 of the prompt, model, ms, tokens) for the runs table.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..config import KEY_ENV, settings

BASE_URL = {"groq": "https://api.groq.com/openai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "openai": "https://api.openai.com/v1"}
DEFAULT_MODEL = {"groq": "llama-3.3-70b-versatile", "gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini"}
SYSTEM = "You are a careful compliance assistant. Reply with one JSON object only, no prose."
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def provider_for(model: str, default: str) -> str:
    m = model.lower()
    if m.startswith("gemini"):
        return "gemini"
    if m.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return default


def _transient(e: Exception) -> bool:
    try:
        import openai
        if isinstance(e, (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)):
            return True
    except ImportError:  # pragma: no cover
        pass
    if getattr(e, "status_code", None) == 429:
        return True
    s = str(e).lower()
    return "rate limit" in s or "429" in s or "timed out" in s or "timeout" in s


def _retry_after(e: Exception, default: float = 2.0, cap: float = 60.0) -> float:
    headers = getattr(getattr(e, "response", None), "headers", None) or {}
    for k in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        v = headers.get(k)
        m = re.fullmatch(r"(?:(\d+)m)?([\d.]+)s?", str(v).strip()) if v else None
        if m:
            return min(cap, float(m.group(1) or 0) * 60 + float(m.group(2)))
    return default


@dataclass
class Usage:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0
    fallbacks: int = 0


@dataclass
class LLMClient:
    """Real client. `step` picks the model from settings ([llm] <step>_model)."""
    usage: Usage = field(default_factory=Usage)
    calls: list[dict] = field(default_factory=list)

    def __post_init__(self):
        cfg = settings()["llm"]
        self.primary, self.fallback = cfg["primary"], cfg.get("fallback")
        self.max_retries = int(cfg.get("max_retries", 2))
        self.timeout = float(cfg.get("timeout_s", 60))
        self.switched = False
        if not os.getenv(KEY_ENV[self.primary]) and not (self.fallback and os.getenv(KEY_ENV[self.fallback])):
            raise LLMError(f"No API key: set {KEY_ENV[self.primary]} (or {KEY_ENV.get(self.fallback, '')}) in .env")
        self._clients: dict[str, object] = {}

    # ---- provider plumbing
    def _client(self, provider: str):
        if provider not in self._clients:
            key = os.getenv(KEY_ENV[provider])
            if not key:
                raise LLMError(f"{KEY_ENV[provider]} is not set")
            from openai import OpenAI
            self._clients[provider] = OpenAI(base_url=BASE_URL[provider], api_key=key, timeout=self.timeout,
                                             max_retries=0)
        return self._clients[provider]

    def model_for(self, step: str | None) -> tuple[str, str]:
        cfg = settings()["llm"]
        model = cfg.get(f"{step}_model") if step else None
        provider = provider_for(model, self.primary) if model else self.primary
        if self.switched and provider == self.primary:  # rest of run on the fallback
            return self.fallback, DEFAULT_MODEL[self.fallback]
        if not os.getenv(KEY_ENV[provider]):  # e.g. verifier on Gemini without a Gemini key
            provider, model = self.primary, None
        return provider, model or DEFAULT_MODEL[provider]

    def _call(self, provider: str, model: str, prompt: str) -> str:
        t0 = time.time()
        resp = self._client(provider).chat.completions.create(
            model=model, temperature=0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
        ms = int((time.time() - t0) * 1000)
        u = resp.usage
        tin, tout = (u.prompt_tokens or 0, u.completion_tokens or 0) if u else (0, 0)
        self.usage.calls += 1
        self.usage.ms += ms
        self.usage.tokens_in += tin
        self.usage.tokens_out += tout
        self.calls.append({"model": model, "provider": provider, "ms": ms, "tokens_in": tin, "tokens_out": tout})
        return resp.choices[0].message.content or ""

    def _complete(self, step: str | None, prompt: str) -> str:
        provider, model = self.model_for(step)
        try:
            return self._call(provider, model, prompt)
        except Exception as e:
            if not _transient(e):
                raise LLMError(f"{provider} request failed: {str(e)[:300]}") from e
            wait = _retry_after(e)
        time.sleep(wait)
        try:
            return self._call(provider, model, prompt)
        except Exception as e:
            if not _transient(e):
                raise LLMError(f"{provider} request failed: {str(e)[:300]}") from e
            last = e
        fb = self.fallback
        if fb and fb != provider and os.getenv(KEY_ENV[fb]):
            self.switched = True
            self.usage.fallbacks += 1
            return self._call(fb, DEFAULT_MODEL[fb], prompt)
        raise LLMError(f"Rate limit or timeout on {provider} and no fallback key: {str(last)[:200]}")

    # ---- public
    def json(self, name: str, prompt: str, schema: type[T], step: str | None = None) -> T:
        invalid = ""
        for _ in range(self.max_retries + 1):
            p = prompt if not invalid else f"{prompt}\n\nYour previous output was invalid: {invalid}\nReturn valid JSON only."
            raw = self._complete(step or name, p)
            if self.calls:
                self.calls[-1].update(prompt=name, prompt_hash=prompt_hash(prompt), output=raw[:4000])
            try:
                return schema.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as e:
                invalid = str(e)[:400]
        raise LLMError(f"{name}: output failed validation after retries: {invalid}")
