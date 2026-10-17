"""Settings from config/settings.toml; secrets only from the environment (or a git-ignored .env)."""
from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repo root (backend/..)
SETTINGS_FILE = ROOT / "config" / "settings.toml"
KEY_ENV = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Fill missing env vars from .env (never overrides real env; values are never printed)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if v.strip():
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@lru_cache(maxsize=1)
def settings() -> dict:
    s = tomllib.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    s["paths"] = {k: (ROOT / v) for k, v in s["paths"].items()}
    if os.getenv("CLAIMGUARD_PUBLIC_DEMO") is not None:
        s["app"]["public_demo"] = os.getenv("CLAIMGUARD_PUBLIC_DEMO", "1") not in ("0", "false", "False")
    return s


def path(name: str) -> Path:
    return settings()["paths"][name]


def key_status() -> dict[str, str]:
    return {p: ("ok" if os.getenv(env) else "missing") for p, env in KEY_ENV.items() if p != "openai"}
