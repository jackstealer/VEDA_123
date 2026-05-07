"""
VEDA — Sub-Agent 5: Competitor Intelligence
Discovers real competitors via GitHub + web signals,
scores them against the target, and produces a competitive landscape report.
"""
import json
import logging
import re
import httpx

from utils.config import GITHUB_TOKEN, MCP_SERVER_URL
from utils.vertex_helper import ask_gemini

logger = logging.getLogger(__name__)

_GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}),
}


class CompetitorIntelligenceAgent:

    def run(
        self,
        job_id: str,
        company_name: str,
        industry: str,
        github_repo_url: str,
        target_scores: dict,
    ) -> dict:
        logger.info("[CompetitorIntel] Scanning competitors for: %s", company_name)

        competitors = self._discover_competitors(
            company_name, industry, github_repo_url
        )
        scored = self._score_competitors(competitors)
        landscape = self._build_landscape(
            company_name, industry, target_scores, scored
        )

        result = {
            "job_id":              job_id,
            "target_company":      company_name,
            "industry":            industry,
            "competitors_found":   len(scored),
            "competitors":         scored,
            "competitive_position": landscape.get("competitive_position"),
            "market_leadership":   landscape.get("market_leadership"),
            "threat_level":        landscape.get("threat_level"),
            "landscape_summary":   landscape.get("landscape_summary"),
            "acquisition_rationale": landscape.get("acquisition_rationale"),
        }

        logger.info(
            "[CompetitorIntel] Found %d competitors — Position: %s",
            len(scored),
            result.get("competitive_position"),
        )
        return result

    # ── Competitor Discovery ──────────────────────────────────────────────────

    def _discover_competitors(
        self, company_name: str, industry: str, repo_url: str
    ) -> list[dict]:
        """
        Use Gemini to identify 3 real competitors, then fetch
        their GitHub metrics for objective scoring.
        """
        prompt = f"""
You are a market research analyst. Identify exactly 3 real competitor companies
for the following target in the {industry} space.

Target Company: {company_name}
Repository: {repo_url}
Industry: {industry}

Rules:
- Return ONLY real, publicly known companies or open-source projects
- Each must have a public GitHub repository
- Prefer direct competitors (same problem, same market)
- Do NOT invent companies

Respond ONLY with valid JSON (no markdown):
{{
  "competitors": [
    {{
      "name": "<company name>",
      "github_url": "<full https://github.com/owner/repo URL>",
      "why_competitor": "<one sentence — specific overlap with target>"
    }},
    {{
      "name": "<company name>",
      "github_url": "<full https://github.com/owner/repo URL>",
      "why_competitor": "<one sentence>"
    }},
    {{
      "name": "<company name>",
      "github_url": "<full https://github.com/owner/repo URL>",
      "why_competitor": "<one sentence>"
    }}
  ]
}}
"""
        raw = ask_gemini(prompt, temperature=0.1, context="CompetitorDiscovery")
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            data  = json.loads(clean)
            return data.get("competitors", [])
        except Exception as exc:
            logger.warning("[CompetitorIntel] Discovery parse failed: %s", exc)
            return []

    # ── GitHub Scoring ────────────────────────────────────────────────────────

    def _score_competitors(self, competitors: list[dict]) -> list[dict]:
        """Fetch real GitHub metrics for each competitor and compute a score."""
        scored = []
        for comp in competitors:
            try:
                metrics = self._fetch_github_metrics(comp.get("github_url", ""))
                score   = self._compute_github_score(metrics)
                scored.append({
                    "name":             comp.get("name"),
                    "github_url":       comp.get("github_url"),
                    "why_competitor":   comp.get("why_competitor"),
                    "github_score":     score,
                    "stars":            metrics.get("stars", 0),
                    "forks":            metrics.get("forks", 0),
                    "contributors":     metrics.get("contributors", 0),
                    "commits_30d":      metrics.get("commits_30d", 0),
                    "has_tests":        metrics.get("has_tests", False),
                    "has_cicd":         metrics.get("has_cicd", False),
                    "days_since_push":  metrics.get("days_since_push", 999),
                    "license":          metrics.get("license", "None"),
                    "language":         metrics.get("primary_language", "Unknown"),
                })
            except Exception as exc:
                logger.warning(
                    "[CompetitorIntel] Failed to score %s: %s",
                    comp.get("name"), exc,
                )
                scored.append({
                    "name":           comp.get("name"),
                    "github_url":     comp.get("github_url"),
                    "why_competitor": comp.get("why_competitor"),
                    "github_score":   50,
                    "error":          str(exc),
                })
        return scored

    def _fetch_github_metrics(self, repo_url: str) -> dict:
        repo_path = repo_url.rstrip("/").split("github.com/")[-1]

        with httpx.Client(follow_redirects=True, timeout=15) as client:
            repo = client.get(
                f"https://api.github.com/repos/{repo_path}",
                headers=_GITHUB_HEADERS,
            ).json()

            commits_resp = client.get(
                f"https://api.github.com/repos/{repo_path}/commits?per_page=30",
                headers=_GITHUB_HEADERS,
            )
            commits = commits_resp.json() if commits_resp.status_code == 200 else []

            cicd_resp = client.get(
                f"https://api.github.com/repos/{repo_path}/contents/.github/workflows",
                headers=_GITHUB_HEADERS,
            )

            tests_found = False
            for d in ["tests", "test", "__tests__"]:
                t = client.get(
                    f"https://api.github.com/repos/{repo_path}/contents/{d}",
                    headers=_GITHUB_HEADERS,
                )
                if t.status_code == 200:
                    tests_found = True
                    break

            langs_resp = client.get(
                f"https://api.github.com/repos/{repo_path}/languages",
                headers=_GITHUB_HEADERS,
            )
            langs = langs_resp.json() if langs_resp.status_code == 200 else {}
            primary_lang = max(langs, key=langs.get) if langs else "Unknown"

        from datetime import datetime, timezone
        def days_since(s):
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return (datetime.now(timezone.utc) - dt).days
            except Exception:
                return 999

        commits_30d = sum(
            1 for c in commits
            if days_since(c.get("commit", {}).get("author", {}).get("date", "")) <= 30
        )

        return {
            "stars":            repo.get("stargazers_count", 0),
            "forks":            repo.get("forks_count", 0),
            "contributors":     0,
            "commits_30d":      commits_30d,
            "has_tests":        tests_found,
            "has_cicd":         cicd_resp.status_code == 200,
            "days_since_push":  days_since(repo.get("pushed_at", "")),
            "license":          repo.get("license", {}).get("name", "None") if repo.get("license") else "None",
            "primary_language": primary_lang,
            "is_archived":      repo.get("archived", False),
        }

    def _compute_github_score(self, m: dict) -> int:
        score = 50
        stars = m.get("stars", 0)
        if stars >= 10000: score += 25
        elif stars >= 1000: score += 15
        elif stars >= 100:  score += 8
        elif stars >= 10:   score += 3

        if m.get("has_tests"):  score += 10
        if m.get("has_cicd"):   score += 8

        commits = m.get("commits_30d", 0)
        if commits >= 10:   score += 8
        elif commits >= 3:  score += 4
        elif commits == 0:  score -= 10

        days = m.get("days_since_push", 999)
        if days > 365:  score -= 20
        elif days > 90: score -= 8

        if m.get("is_archived"): score -= 30

        return max(0, min(100, score))

    # ── Competitive Landscape ─────────────────────────────────────────────────

    def _build_landscape(
        self,
        company_name: str,
        industry: str,
        target_scores: dict,
        competitors: list[dict],
    ) -> dict:
        comp_summary = "\n".join([
            f"- {c['name']}: GitHub Score {c.get('github_score')}/100, "
            f"Stars {c.get('stars', 0):,}, "
            f"Active: {'Yes' if c.get('commits_30d', 0) > 0 else 'No'}, "
            f"Why competitor: {c.get('why_competitor', '')}"
            for c in competitors
        ])

        prompt = f"""
You are a senior M&A analyst producing a competitive landscape assessment.

Target Company: {company_name}
Industry: {industry}

Target Scores:
- Tech Debt Score:  {target_scores.get('tech_debt_score', 'N/A')}/100
- Compliance Score: {target_scores.get('compliance_score', 'N/A')}/100
- Market Fit Score: {target_scores.get('market_fit_score', 'N/A')}/100

Identified Competitors:
{comp_summary}

Assess the competitive position of the TARGET company relative to these competitors.
Be specific — cite star counts, activity levels, scores.

Respond ONLY with valid JSON (no markdown):
{{
  "competitive_position": "<MARKET LEADER | STRONG CHALLENGER | COMPETITIVE | NICHE PLAYER | LAGGARD>",
  "market_leadership":    "<percentage estimate of market share or mindshare>",
  "threat_level":         "<LOW | MEDIUM | HIGH — threat from competitors to acquisition value>",
  "landscape_summary":    "<4-5 sentences — specific competitive analysis citing real data>",
  "acquisition_rationale": "<2-3 sentences — why acquiring THIS company makes sense vs competitors>"
}}
"""
        raw = ask_gemini(prompt, temperature=0.2, context="CompetitorLandscape")
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except Exception as exc:
            logger.warning("[CompetitorIntel] Landscape parse failed: %s", exc)
            return {
                "competitive_position":  "UNKNOWN",
                "market_leadership":     "N/A",
                "threat_level":          "MEDIUM",
                "landscape_summary":     raw[:400],
                "acquisition_rationale": "Insufficient data.",
            }
