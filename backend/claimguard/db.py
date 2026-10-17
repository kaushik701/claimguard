"""App database (SQLite via SQLModel). Tables per docs/ARCHITECTURE.md."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, create_engine

from .config import path


def now() -> datetime:
    return datetime.now(timezone.utc)


class Audit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now)
    input_type: str = "text"
    surface: str = "ecommerce"
    category: str = "home"
    brand: str = ""
    paid: bool = False
    text: str = ""
    image_path: Optional[str] = None
    ocr_boxes: list = Field(default_factory=list, sa_column=Column(JSON))
    mode: str = "llm"
    status: str = "queued"           # queued | running | done | error
    steps: list = Field(default_factory=list, sa_column=Column(JSON))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))   # not_covered, low_risk, dropped, stats
    fallback_used: bool = False
    error: Optional[str] = None
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Optional[float] = None


class ClaimRow(SQLModel, table=True):
    __tablename__ = "claims"
    id: Optional[int] = Field(default=None, primary_key=True)
    audit_id: int = Field(index=True)
    text: str
    start: int = -1
    end: int = -1
    claim_type: str = ""
    alt_types: list = Field(default_factory=list, sa_column=Column(JSON))
    source: str = "rule"
    qualifier: bool = False
    source_date: bool = False


class FlagRow(SQLModel, table=True):
    __tablename__ = "flags"
    id: Optional[int] = Field(default=None, primary_key=True)
    audit_id: int = Field(index=True)
    claim_id: int = Field(index=True)
    risk: str
    reason: str = ""
    rewrite: Optional[str] = None
    confidence: Optional[float] = None
    verifier_note: Optional[str] = None
    status: str = Field(default="open", index=True)
    reviewer_risk: Optional[str] = None
    reviewer_note: Optional[str] = None


class CitationRow(SQLModel, table=True):
    __tablename__ = "citations"
    id: Optional[int] = Field(default=None, primary_key=True)
    flag_id: int = Field(index=True)
    clause_id: str
    quote: str
    rank: int = 0


class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    flag_id: int = Field(index=True)
    action: str
    from_risk: Optional[str] = None
    to_risk: Optional[str] = None
    reason_code: Optional[str] = None
    note: Optional[str] = None
    reviewer: Optional[str] = None
    created_at: datetime = Field(default_factory=now)


class Run(SQLModel, table=True):
    __tablename__ = "runs"
    id: Optional[int] = Field(default=None, primary_key=True)
    audit_id: Optional[int] = Field(default=None, index=True)
    step: str
    model: str = ""
    prompt_hash: str = ""
    input_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    output_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error: Optional[str] = None


class EvalRun(SQLModel, table=True):
    __tablename__ = "eval_runs"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now)
    set_name: str
    config_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    metrics_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    report_path: str = ""


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    id: Optional[int] = Field(default=None, primary_key=True)
    turns: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)


_ENGINES: dict[str, object] = {}


def engine(url: str | None = None):
    url = url or f"sqlite:///{path('db')}"
    if url not in _ENGINES:
        if url.startswith("sqlite:///") and url != "sqlite://":
            from pathlib import Path
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        e = create_engine(url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(e)
        _ENGINES[url] = e
    return _ENGINES[url]


def session(url: str | None = None) -> Session:
    return Session(engine(url))
