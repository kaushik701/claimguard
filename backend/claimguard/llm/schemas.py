"""Pydantic schemas for every prompt's JSON output (docs/prompts/SYSTEM_PROMPTS.md)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

CLAIM_TYPES = ["efficacy", "comparative", "leadership", "time_bound", "appearance", "scientific", "environmental",
               "natural_purity", "nutrition_health", "awards_rankings", "pricing_offer", "celebrity_endorsement",
               "puffery"]
TAG_TYPES = CLAIM_TYPES + ["disclosure", "children", "gender", "general_truthfulness"]
TAG_CATEGORIES = ["all", "food", "beauty", "personal", "home"]
TAG_SURFACES = ["all", "social_post", "ecommerce", "quick_commerce", "brand_site", "tv_print"]


class TagOut(BaseModel):  # P1
    claim_types: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    administrative: bool = False
    rationale: str = ""


class TagBatchItem(TagOut):
    clause_id: str


class TagBatchOut(BaseModel):
    items: list[TagBatchItem] = Field(default_factory=list)


class VisionBlock(BaseModel):
    text: str
    position: str = ""


class VisionOut(BaseModel):  # P2
    blocks: list[VisionBlock] = Field(default_factory=list)
    notes: Optional[str] = None


class XClaim(BaseModel):
    text: str
    claim_type: str
    footnote_text: Optional[str] = None
    has_qualifier: bool = False


class ExtractOut(BaseModel):  # P3
    claims: list[XClaim] = Field(default_factory=list)


class QueriesOut(BaseModel):  # P4
    queries: list[str] = Field(default_factory=list)


class Ranked(BaseModel):
    clause_id: str
    score: int = Field(ge=0, le=3)
    why: str = ""


class RerankOut(BaseModel):  # P5
    ranked: list[Ranked] = Field(default_factory=list)


class Cit(BaseModel):
    clause_id: str
    quote: str


class Assessment(BaseModel):
    claim_index: int
    risk: Literal["high", "medium", "low"]
    reason: str
    evidence_span: str = ""
    citations: list[Cit] = Field(default_factory=list)
    rewrite: Optional[str] = None
    confidence: float = Field(0.7, ge=0, le=1)


class JudgeOut(BaseModel):  # P6
    assessments: list[Assessment] = Field(default_factory=list)


class Verdict(BaseModel):
    flag_index: int
    supports: bool
    confidence: float = Field(0.7, ge=0, le=1)
    issue: Optional[str] = None


class VerifyOut(BaseModel):  # P7
    verdicts: list[Verdict] = Field(default_factory=list)


class Rewrite(BaseModel):
    flag_index: int
    text: str


class RewriteOut(BaseModel):  # P8
    rewrites: list[Rewrite] = Field(default_factory=list)


class CopilotCit(BaseModel):
    n: int
    clause_id: str
    quote: str


class CopilotOut(BaseModel):  # P9
    answer: str
    citations: list[CopilotCit] = Field(default_factory=list)
    covered: bool = True


class QuestionOut(BaseModel):  # P10
    question: str


class ReportOut(BaseModel):  # P11
    summary: str
    suggestions: list[str] = Field(default_factory=list)
