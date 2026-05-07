"""
VEDA — Sub-Agent 3: Market Analyst (Enhanced)
Uses real GitHub metrics + compliance data to drive accurate 3-year forecast.
"""

import json
import re
from utils.vertex_helper import ask_gemini

# Industry ARR benchmarks for Indian startups (INR Lakhs)
INDUSTRY_BENCHMARKS = {
    "fintech": {
        "avg_seed_arr": 50,
        "avg_series_a_arr": 500,
        "typical_growth_rate": 120,
        "valuation_multiple_base": 8,
        "market_size_cr": 150000,
    },
    "healthtech": {
        "avg_seed_arr": 30,
        "avg_series_a_arr": 300,
        "typical_growth_rate": 80,
        "valuation_multiple_base": 6,
        "market_size_cr": 50000,
    },
    "edtech": {
        "avg_seed_arr": 40,
        "avg_series_a_arr": 400,
        "typical_growth_rate": 60,
        "valuation_multiple_base": 5,
        "market_size_cr": 30000,
    },
    "saas": {
        "avg_seed_arr": 80,
        "avg_series_a_arr": 800,
        "typical_growth_rate": 100,
        "valuation_multiple_base": 10,
        "market_size_cr": 80000,
    },
    "ecommerce": {
        "avg_seed_arr": 100,
        "avg_series_a_arr": 1000,
        "typical_growth_rate": 70,
        "valuation_multiple_base": 4,
        "market_size_cr": 200000,
    },
    "deeptech": {
        "avg_seed_arr": 20,
        "avg_series_a_arr": 200,
        "typical_growth_rate": 90,
        "valuation_multiple_base": 12,
        "market_size_cr": 40000,
    },
    "default": {
        "avg_seed_arr": 50,
        "avg_series_a_arr": 500,
        "typical_growth_rate": 80,
        "valuation_multiple_base": 7,
        "market_size_cr": 50000,
    },
}


class MarketAnalystAgent:

    def run(self, job_id: str, company_name: str, industry: str,
            tech_debt_score: float, compliance_score: float,
            github_data: dict = None) -> dict:
        print(f"[MarketAnalyst] Running 3-year simulation for: {company_name}")

        market_fit = self._compute_market_fit(
            tech_debt_score, compliance_score, github_data or {}
        )
        benchmark  = self._get_benchmark(industry)
        prompt     = self._build_prompt(
            company_name, industry, tech_debt_score,
            compliance_score, market_fit, benchmark, github_data or {}
        )
        raw    = ask_gemini(prompt)
        result = self._parse(raw)

        result["market_fit_score"] = market_fit
        result["job_id"]           = job_id

        print(f"[MarketAnalyst] Market fit: {market_fit}")
        return result

    def _compute_market_fit(self, tech_debt: float,
                             compliance: float, github_data: dict) -> float:
        """
        Compute market fit using real signals:
        - Tech debt (code quality) affects scaling ability
        - Compliance affects enterprise sales
        - GitHub popularity signals market traction
        - Activity signals team health
        """
        # Base score from existing agents
        base = tech_debt * 0.40 + compliance * 0.30

        # GitHub traction signals (up to 20 points)
        stars = github_data.get("stars", 0)
        if stars >= 10000:
            traction = 20
        elif stars >= 1000:
            traction = 15
        elif stars >= 100:
            traction = 10
        elif stars >= 10:
            traction = 5
        else:
            traction = 0

        # Activity health (up to 10 points)
        commits_30d = github_data.get("commits_last_30_days", 0)
        activity = min(commits_30d * 1.5, 10)

        return round(min(100, base + traction + activity), 2)

    def _get_benchmark(self, industry: str) -> dict:
        key = industry.lower().replace(" ", "").replace("-", "")
        for k in INDUSTRY_BENCHMARKS:
            if k in key:
                return INDUSTRY_BENCHMARKS[k]
        return INDUSTRY_BENCHMARKS["default"]

    def _build_prompt(self, company_name, industry, tech_debt,
                       compliance, market_fit, benchmark, github_data) -> str:
        stars        = github_data.get("stars", 0)
        forks        = github_data.get("forks", 0)
        contributors = github_data.get("contributors_count", 0)
        commits_30d  = github_data.get("commits_last_30_days", 0)
        days_since   = github_data.get("days_since_push", 999)

        return f"""
You are a senior investment analyst at a tier-1 venture capital fund in India.
Build a data-driven 3-year growth simulation for a potential M&A target.

Company: {company_name}
Industry: {industry}
Market Fit Score: {market_fit}/100

=== REAL SIGNALS ===
Technical Health:
- Tech Debt Score: {tech_debt}/100
- Compliance Score: {compliance}/100

GitHub Traction:
- Stars: {stars:,} (community adoption signal)
- Forks: {forks:,} (developer interest signal)
- Contributors: {contributors} (team depth signal)
- Commits in last 30 days: {commits_30d} (activity signal)
- Days since last commit: {days_since}

=== INDUSTRY BENCHMARKS (India) ===
- Average Seed ARR: INR {benchmark['avg_seed_arr']}L
- Average Series A ARR: INR {benchmark['avg_series_a_arr']}L
- Typical Annual Growth Rate: {benchmark['typical_growth_rate']}%
- Base Valuation Multiple: {benchmark['valuation_multiple_base']}x ARR
- Total Market Size: INR {benchmark['market_size_cr']} Cr

=== SCORING CONTEXT ===
- High tech debt (score < 50) = slower feature velocity, higher engineering costs
- Low compliance (score < 50) = enterprise sales blockers, regulatory risk
- Low GitHub activity = team risk or product stagnation
- High stars = proven market demand

Use these real signals to produce REALISTIC scenario forecasts.
Bear = things go wrong (debt compounds, slow growth)
Base = current trajectory maintained
Bull = debt resolved, compliance achieved, strong execution

Respond ONLY with a valid JSON object (no markdown, no extra text):

{{
  "simulation_year": 3,
  "base_assumptions": {{
    "current_arr_estimate_inr_lakhs": <realistic number based on signals>,
    "current_team_size": <estimate based on contributors>,
    "primary_growth_driver": "<specific to this company's signals>"
  }},
  "scenarios": {{
    "bear": {{
      "probability": "<percentage>",
      "year1_arr_inr_lakhs": <number>,
      "year2_arr_inr_lakhs": <number>,
      "year3_arr_inr_lakhs": <number>,
      "year3_headcount": <number>,
      "key_risk": "<specific risk based on the signals>",
      "valuation_multiple": <number>
    }},
    "base": {{
      "probability": "<percentage>",
      "year1_arr_inr_lakhs": <number>,
      "year2_arr_inr_lakhs": <number>,
      "year3_arr_inr_lakhs": <number>,
      "year3_headcount": <number>,
      "key_driver": "<specific driver based on signals>",
      "valuation_multiple": <number>
    }},
    "bull": {{
      "probability": "<percentage>",
      "year1_arr_inr_lakhs": <number>,
      "year2_arr_inr_lakhs": <number>,
      "year3_arr_inr_lakhs": <number>,
      "year3_headcount": <number>,
      "key_driver": "<specific driver>",
      "valuation_multiple": <number>
    }}
  }},
  "recommended_acquisition_price_range_inr_cr": {{
    "min": <number>,
    "max": <number>
  }},
  "forecast_summary": "<3-4 sentence data-driven summary citing actual signals>"
}}
"""

    def _parse(self, raw: str) -> dict:
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except Exception:
            return {
                "market_fit_score": 50,
                "simulation_year":  3,
                "scenarios":        {},
                "forecast_summary": raw[:300],
                "recommended_acquisition_price_range_inr_cr": {"min": 0, "max": 0},
            }