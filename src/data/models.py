from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    STRONG = "적극추천"
    REVIEW = "검토"
    PASS = "패스"


class PrefilterStatus(str, Enum):
    PASSED = "통과"
    BLOCKED = "차단"
    WARNING = "경고"


class TrackRecord(BaseModel):
    project_name: str
    year: int
    amount: int
    client: str
    category: str

    @property
    def amount_display(self) -> str:
        if self.amount >= 10**8:
            return f"{self.amount / 10**8:.0f}억원"
        return f"{self.amount / 10**4:.0f}만원"


class TechnicalStaff(BaseModel):
    count: int
    breakdown: dict[str, int]
    senior_above: int


class RiskItem(BaseModel):
    item: str
    risk: str
    severity: Literal["high", "medium", "low"]
    desc: str


class CompanyProfile(BaseModel):
    name: str = "KIA"
    stock_code: str | None = None
    business_type: str | None = None
    capital: int | None = None
    established: str | None = None
    employees: int | None = None
    licenses: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    track_records: list[TrackRecord] = Field(default_factory=list)
    technical_staff: TechnicalStaff | None = None
    preferred_regions: list[str] = Field(default_factory=list)
    target_categories: list[str] = Field(default_factory=list)
    min_project_amount: int = 1_000_000_000


class BidRecord(BaseModel):
    bid_id: str
    title: str
    category: str
    agency: str
    budget: int
    deadline: date
    duration_months: int
    region: str | None = None
    qualifications: list[str] = Field(default_factory=list)
    eval_criteria: dict[str, int] = Field(default_factory=dict)
    risky_items: list[RiskItem] = Field(default_factory=list)
    markdown: str = ""


class QualificationMatch(BaseModel):
    requirement: str
    status: Literal["충족", "부분충족", "미충족", "확인불가"]
    evidence: str
    kia_evidence: str


class ScoreBreakdown(BaseModel):
    qualification_fit: float = 0.0
    budget_fit: float = 0.0
    track_record_match: float = 0.0
    eval_criteria_advantage: float = 0.0
    risk_penalty: float = 0.0


class PrefilterResult(BaseModel):
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    days_left: int | None = None
    urgent: bool = False


class ScreeningResult(BaseModel):
    bid_id: str
    title: str
    category: str
    agency: str
    budget: int
    deadline: date
    days_left: int | None
    urgent: bool
    # 사전필터
    prefilter_blocked: bool
    prefilter_reasons: list[str]
    # 자격매칭
    qualification_matches: list[QualificationMatch]
    qualification_pass: bool
    # 스코어링
    score: float
    grade: Recommendation
    reason: str
    breakdown: ScoreBreakdown
    # 리스크
    risks: list[str]


class ScreeningReport(BaseModel):
    generated_at: str
    corpus: str
    company: str
    total: int
    filtered_out: int
    screened_count: int
    counts: dict[str, int]
    screening_items: list[ScreeningResult]
    total_latency_ms: int