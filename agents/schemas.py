from pydantic import BaseModel, Field
from typing import List, Optional

class CodeAuditResult(BaseModel):
    tech_debt_score: int = Field(..., ge=0, le=100)
    security_flags: List[str]
    strengths: List[str]
    risks: List[str]
    code_quality_summary: str
    recommended_actions: List[str]
    bus_factor_risk: str # LOW | MEDIUM | HIGH
    maintenance_health: str # ACTIVE | MODERATE | STALE | ABANDONED

class RegulatoryResult(BaseModel):
    compliance_score: int = Field(..., ge=0, le=100)
    red_flags: List[str]
    compliance_frameworks_met: List[str]
    missing_requirements: List[str]
    regulatory_summary: str
    recommendation: str # PROCEED | INVESTIGATE | AVOID

class Scenario(BaseModel):
    probability: str # e.g. "30%"
    year3_arr_inr_lakhs: float
    year3_headcount: int
    key_driver: str
    key_risk: str

class MarketForecastResult(BaseModel):
    market_fit_score: int = Field(..., ge=0, le=100)
    market_size_vibe: str
    competitive_advantage: str
    scenarios: dict # { "bear": Scenario, "base": Scenario, "bull": Scenario }
    market_summary: str

class ExecutiveSummaryResult(BaseModel):
    overall_risk_score: int = Field(..., ge=0, le=100)
    recommendation: str # PROCEED | PROCEED WITH CONDITIONS | DO NOT PROCEED
    overall_rating: str # STRONG BUY | BUY | HOLD | AVOID
    one_line_verdict: str
    executive_summary: str
    key_strengths: List[str]
    key_concerns: List[str]
    conditions_for_deal: List[str]

class Competitor(BaseModel):
    name: str
    strength: str
    weakness: str
    market_share_vibe: str # e.g. "Dominant", "Niche", "Rising"

class MarketScoutResult(BaseModel):
    competitors: List[Competitor]
    swot_analysis: dict # { "strengths": [], "weaknesses": [], "opportunities": [], "threats": [] }
    market_differentiation: str
    competitive_risk_score: int = Field(..., ge=0, le=100)

class FinancialResult(BaseModel):
    arr_inr_lakhs: float
    growth_rate_yoy_pct: float
    monthly_burn_inr_lakhs: float
    runway_months: int
    gross_margin_pct: int
    valuation_multiple: float
    financial_health_score: int = Field(..., ge=0, le=100)
    financial_summary: str
