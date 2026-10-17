"""FakeLLM for tests and offline evals: answers by prompt name from (1) a handler function, (2) a recorded
fixture keyed by prompt name + prompt hash (backend/tests/fixtures/llm/<name>/<hash>.json), else (3) raises.
Same interface as LLMClient.json. Never touches the network."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .client import LLMError, Usage, prompt_hash

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "llm"


@dataclass
class FakeLLM:
    handlers: dict[str, Callable[[str], dict]] = field(default_factory=dict)
    fixtures: Path = FIXTURES
    usage: Usage = field(default_factory=Usage)
    calls: list[dict] = field(default_factory=list)

    def json(self, name, prompt, schema, step=None):
        h = prompt_hash(prompt)
        self.usage.calls += 1
        self.calls.append({"prompt": name, "prompt_hash": h, "model": "fake", "ms": 0, "tokens_in": 0,
                           "tokens_out": 0})
        if name in self.handlers:
            return schema.model_validate(self.handlers[name](prompt))
        f = self.fixtures / name / f"{h}.json"
        if f.exists():
            return schema.model_validate(json.loads(f.read_text(encoding="utf-8")))
        raise LLMError(f"FakeLLM: no handler or fixture for {name}/{h}")


class RecordingLLM:
    """Wraps a real client and saves each validated answer as a fixture (record once, replay in CI)."""

    def __init__(self, inner, fixtures: Path = FIXTURES):
        self.inner, self.fixtures = inner, fixtures
        self.usage, self.calls = inner.usage, inner.calls

    def json(self, name, prompt, schema, step=None):
        out = self.inner.json(name, prompt, schema, step)
        d = self.fixtures / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{prompt_hash(prompt)}.json").write_text(out.model_dump_json(indent=1), encoding="utf-8")
        return out
