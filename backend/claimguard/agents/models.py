"""Typed objects passed between agent steps (mirrors docs/API_CONTRACT.md core types)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Risk = Literal["high", "medium", "low"]


class Claim(BaseModel):
    id: str = ""
    text: str
    start: int
    end: int
    claim_type: str
    alt_types: list[str] = Field(default_factory=list)
    source: Literal["llm", "rule", "both"] = "rule"
    qualifier: bool = False
    source_date: bool = False
    footnote_text: Optional[str] = None


class Citation(BaseModel):
    clause_id: str
    doc_id: str = ""
    doc_title: str = ""
    section_path: str = ""
    number: Optional[str] = None
    page: int = 0
    quote: str
    source: Literal["text", "ocr", "vision"] = "text"
    ocr_conf: Optional[float] = None


class Flag(BaseModel):
    claim: Claim
    risk: Risk
    reason: str
    evidence_span: str = ""
    rewrite: Optional[str] = None
    confidence: Optional[float] = None
    verifier_note: Optional[str] = None
    citations: list[Citation] = Field(default_factory=list)
    judge: Literal["llm", "rule"] = "llm"


class Dropped(BaseModel):
    claim: str
    reason: str
    stage: str  # citation_guard | verifier | ocr_guard


class AuditOutput(BaseModel):
    text: str
    claims: list[Claim] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    not_covered: list[Claim] = Field(default_factory=list)
    low_risk: list[Claim] = Field(default_factory=list)
    dropped: list[Dropped] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    steps: list[dict] = Field(default_factory=list)
