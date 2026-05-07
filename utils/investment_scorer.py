"""
VEDA — Auto Investment Score (0-100)
Combines sentiment, financial signals, and keyword heuristics.
Modular — each component can be tuned independently.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Weights (must sum to 1.0) ─────────────────────────────────────────────────
_W_TECH         = 0.25
_W_COMPLIANCE   = 0.20
_W_MARKET       = 0.20
_W_SENTIMENT    = 0.15
_W_FINANCIAL    = 0.10
_W_KEYWORDS     = 0.10

# ── Keyword signals ───────────────────────────────────────────────────────────
_POSITIVE_KEYWORDS = [
    "profitable", "revenue growth", "series b", "series c", "ipo",
    "market leader", "patent", "enterprise", "b2b", "saas",
    "recurring revenue", "arr", "mrr", "expansion", "international",
]
_NEGATIVE_KEYWORDS = [
    "pre-revenue", "no customers", "pivot", "lawsuit", "investigation",
    "burning cash", "no traction", "failed", "shutdown", "debt",
]


def compute_investment_score(
    tech_debt_score: float,
    compliance_score: float,
    market_fit_score: float,
    sentiment_score: float,          # -1 to +1
    sentiment_magnitude: float,
    pitch_text: str = "",
    financial_signals: dict = None,
) -> dict:
    """
    Compute a 0-100 investment score from all available signals.

    Returns:
        score (int): 0-100
        breakdown (dict): per-component contribution
        grade (str): A/B/C/D/F
        recommendation (str): invest / watch / avoid
    """
    fs = financial_signals or {}

    # ── Component 1: Technical health (0-100) ────────────────────────────────
    tech_component = float(tech_debt_score or 50)

    # ── Component 2: Compliance (0-100) ──────────────────────────────────────
    compliance_component = float(compliance_score or 50)

    # ── Component 3: Market fit (0-100) ──────────────────────────────────────
    market_component = float(market_fit_score or 50)

    # ── Component 4: Sentiment (convert -1..+1 to 0..100) ────────────────────
    sentiment_component = (float(sentiment_score) + 1) / 2 * 100
    # Weight by magnitude (high magnitude = more conviction)
    magnitude_boost = min(float(sentiment_magnitude) * 5, 10)
    sentiment_component = min(sentiment_component + magnitude_boost, 100)

    # ── Component 5: Financial signals (0-100) ────────────────────────────────
    financial_component = _score_financial_signals(fs)

    # ── Component 6: Keyword heuristics (0-100) ───────────────────────────────
    keyword_component = _score_keywords(pitch_text)

    # ── Weighted composite ─────────────────────────────────────────────────────
    raw_score = (
        tech_component       * _W_TECH       +
        compliance_component * _W_COMPLIANCE +
        market_component     * _W_MARKET     +
        sentiment_component  * _W_SENTIMENT  +
        financial_component  * _W_FINANCIAL  +
        keyword_component    * _W_KEYWORDS
    )

    score = round(min(max(raw_score, 0), 100))
    grade = _grade(score)
    recommendation = "INVEST" if score >= 70 else "WATCH" if score >= 45 else "AVOID"

    logger.info(
        "[InvestmentScorer] Score=%d Grade=%s Recommendation=%s",
        score, grade, recommendation,
    )

    return {
        "investment_score": score,
        "grade":            grade,
        "recommendation":   recommendation,
        "breakdown": {
            "technical_health": round(tech_component * _W_TECH, 1),
            "compliance":       round(compliance_component * _W_COMPLIANCE, 1),
            "market_fit":       round(market_component * _W_MARKET, 1),
            "sentiment":        round(sentiment_component * _W_SENTIMENT, 1),
            "financial":        round(financial_component * _W_FINANCIAL, 1),
            "keywords":         round(keyword_component * _W_KEYWORDS, 1),
        },
        "weights": {
            "tech": _W_TECH, "compliance": _W_COMPLIANCE,
            "market": _W_MARKET, "sentiment": _W_SENTIMENT,
            "financial": _W_FINANCIAL, "keywords": _W_KEYWORDS,
        },
    }


def _score_financial_signals(fs: dict) -> float:
    """Score financial signals 0-100."""
    if not fs:
        return 50.0  # neutral if no data

    score = 50.0
    revenue = fs.get("revenue_inr_lakhs", 0) or 0
    if revenue > 1000:   score += 30
    elif revenue > 100:  score += 15
    elif revenue > 10:   score += 5
    elif revenue == 0:   score -= 15

    growth = fs.get("growth_rate_pct", 0) or 0
    if growth > 100:  score += 20
    elif growth > 50: score += 10
    elif growth < 0:  score -= 20

    if fs.get("profitable"):     score += 15
    if fs.get("has_debt"):       score -= 10
    if fs.get("series_b_plus"):  score += 10

    return min(max(score, 0), 100)


def _score_keywords(text: str) -> float:
    """Score based on presence of positive/negative keywords."""
    if not text:
        return 50.0
    text_lower = text.lower()
    pos = sum(1 for kw in _POSITIVE_KEYWORDS if kw in text_lower)
    neg = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in text_lower)
    total = max(pos + neg, 1)
    ratio = (pos - neg) / total
    return min(max(50 + ratio * 50, 0), 100)


def _grade(score: int) -> str:
    if score >= 85: return "A+"
    if score >= 75: return "A"
    if score >= 65: return "B"
    if score >= 55: return "C"
    if score >= 40: return "D"
    return "F"
