"""
VEDA — Sub-Agent 4: Executive Summary
Synthesises all agent outputs into a structured board-level recommendation
using a weighted scoring matrix — not free-form Gemini opinion.
"""
import json
import logging
import re
from utils.vertex_helper import ask_gemini

logger = logging.getLogger(__name__)

# Weighted scoring matrix for final recommendation
_WEIGHTS = {
    "tech_debt":   0.35,
    "compliance":  0.35,
    "market_fit":  0.30,
}

_RATING_BANDS = [
    (85, "STRONG BUY",  "PROCEED"),
    (70, "BUY",         "PROCEED"),
    (55, "HOLD",        "PROCEED WITH CONDITIONS"),
    (40, "CAUTIOUS",    "PROCEED WITH CONDITIONS"),
    (0,  "AVOID",       "DO NOT PROCEED"),
]


class ExecutiveSummaryAgent:

    def run(
        self,
        job_id: str,
        company_name: str,
        code_results: dict,
        reg_results: dict,
        market_results: dict,
    ) -> dict:
        logger.info("[ExecutiveSummary] Generating report for: %s", company_name)

        composite = self._composite_score(code_results, reg_results, market_results)
        rating, recommendation = self._band(composite)

        prompt = self._build_prompt(
            company_name, code_results, reg_results,
            market_results, composite, rating, recommendation,
        )
        raw    = ask_gemini(prompt, context="ExecutiveSummary")
        result = self._parse(raw)

        # Override Gemini's recommendation with the deterministic matrix result
        # Gemini is used for qualitative narrative only — not the verdict.
        result["recommendation"]  = recommendation
        result["overall_rating"]  = rating
        result["composite_score"] = composite
        result["score_breakdown"] = {
            "tech_debt_weighted":  round(code_results.get("tech_debt_score", 0) * _WEIGHTS["tech_debt"], 1),
            "compliance_weighted": round(reg_results.get("compliance_score", 0) * _WEIGHTS["compliance"], 1),
            "market_fit_weighted": round(market_results.get("market_fit_score", 0) * _WEIGHTS["market_fit"], 1),
        }
        result["job_id"] = job_id

        logger.info(
            "[ExecutiveSummary] Composite: %.1f | Rating: %s | Verdict: %s",
            composite, rating, recommendation,
        )
        return result

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _composite_score(self, code: dict, reg: dict, market: dict) -> float:
        tech   = code.get("tech_debt_score",   50) or 50
        comp   = reg.get("compliance_score",   50) or 50
        mfit   = market.get("market_fit_score", 50) or 50

        # Hard penalty: deal-blocking regulatory issue
        if reg.get("regulatory_deal_blocker"):
            comp = min(comp, 20)

        # Hard penalty: archived or abandoned repo
        raw_github = code.get("raw_github_data", {})
        if raw_github.get("is_archived"):
            tech = min(tech, 15)

        return round(
            tech  * _WEIGHTS["tech_debt"]  +
            comp  * _WEIGHTS["compliance"] +
            mfit  * _WEIGHTS["market_fit"],
            1,
        )

    def _band(self, score: float) -> tuple[str, str]:
        for threshold, rating, recommendation in _RATING_BANDS:
            if score >= threshold:
                return rating, recommendation
        return "AVOID", "DO NOT PROCEED"

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        company_name: str,
        code: dict,
        reg: dict,
        market: dict,
        composite: float,
        rating: str,
        recommendation: str,
    ) -> str:
        price = market.get("recommended_acquisition_price_range_inr_cr", {})
        scenarios = market.get("scenarios", {})
        base_arr = scenarios.get("base", {}).get("year3_arr_inr_lakhs", "N/A")

        return f"""
You are the Managing Partner of a tier-1 M&A advisory firm writing a board memo.
The investment committee has already determined the verdict using a scoring matrix.
Your role is to write the qualitative narrative that supports it.

=== VERDICT (DO NOT CHANGE) ===
Recommendation:   {recommendation}
Rating:           {rating}
Composite Score:  {composite}/100

=== INPUTS ===
Company: {company_name}

Technical Due Diligence:
- Tech Debt Score:     {code.get('tech_debt_score')}/100
- Maintenance Health:  {code.get('maintenance_health', 'N/A')}
- Bus Factor Risk:     {code.get('bus_factor_risk', 'N/A')}
- Security Flags:      {code.get('security_flags', [])}
- Key Risks:           {code.get('risks', [])}
- Key Strengths:       {code.get('strengths', [])}

Regulatory:
- Compliance Score:       {reg.get('compliance_score')}/100
- Deal Blocker:           {reg.get('regulatory_deal_blocker', False)}
- Red Flags:              {reg.get('red_flags', [])}
- Remediation Timeline:   {reg.get('estimated_remediation_time', 'N/A')}

Market:
- Market Fit Score:       {market.get('market_fit_score')}/100
- Year 3 Base ARR:        ₹{base_arr}L
- Acquisition Range:      ₹{price.get('min', 0)}Cr — ₹{price.get('max', 0)}Cr
- Forecast Summary:       {market.get('forecast_summary', '')}

=== INSTRUCTIONS ===
Write a professional board memo narrative. Be specific — cite actual numbers.
Do not be generic. Do not repeat the verdict — explain WHY.

Respond ONLY with valid JSON (no markdown, no extra text):

{{
  "executive_summary": "<5-7 sentence board-level memo citing specific scores and signals>",
  "one_line_verdict": "<single crisp sentence — specific to this company, not generic>",
  "key_strengths": [<3 specific strengths with evidence from the data>],
  "key_concerns": [<3 specific concerns with evidence from the data>],
  "conditions_for_deal": [<specific pre-closing conditions — empty list if PROCEED or DO NOT PROCEED>],
  "confidence_level": "<HIGH | MEDIUM | LOW — based on data completeness>"
}}
"""

    # ── Parse ─────────────────────────────────────────────────────────────────

    def _parse(self, raw: str) -> dict:
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except Exception:
            logger.warning("[ExecutiveSummary] JSON parse failed — using fallback")
            return {
                "executive_summary":  raw[:500] if raw else "Analysis incomplete.",
                "one_line_verdict":   "Insufficient data for verdict.",
                "key_strengths":      [],
                "key_concerns":       [],
                "conditions_for_deal": [],
                "confidence_level":   "LOW",
            }
