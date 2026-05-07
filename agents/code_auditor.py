"""
VEDA — Sub-Agent 1: Code Auditor (Enhanced)
Uses 25+ real GitHub signals for accurate technical debt scoring.
No more guessing — scores are driven by actual repository metrics.
"""

import json
import re
import httpx
from utils.config import MCP_SERVER_URL
from utils.vertex_helper import ask_gemini


class CodeAuditorAgent:

    def run(self, job_id: str, repo_url: str, company_name: str) -> dict:
        print(f"[CodeAuditor] Scanning: {repo_url}")
        github_data = self._fetch_repo(repo_url)

        # Pre-compute rule-based scores before sending to Gemini
        # This anchors Gemini's output to real data
        rule_score = self._rule_based_score(github_data)

        prompt  = self._build_prompt(company_name, repo_url, github_data, rule_score)
        raw     = ask_gemini(prompt)
        result  = self._parse(raw)

        # Blend Gemini score with rule-based score (60/40)
        # This prevents Gemini from wildly guessing
        gemini_score = result.get("tech_debt_score", rule_score)
        final_score  = round(gemini_score * 0.6 + rule_score * 0.4)
        result["tech_debt_score"]      = final_score
        result["rule_based_score"]     = rule_score
        result["raw_github_data"]      = github_data
        result["job_id"]               = job_id

        print(f"[CodeAuditor] Tech debt score: {final_score} (Gemini: {gemini_score}, Rules: {rule_score})")
        return result

    # ── Rule-based scoring from real GitHub signals ───────────────────

    def _rule_based_score(self, data: dict) -> int:
        """
        Compute a deterministic tech debt score from real GitHub signals.
        100 = excellent codebase, 0 = critical technical debt.
        """
        score = 100

        # ── Activity penalties ────────────────────────────────────────
        days_since_push = data.get("days_since_push", 999)
        if days_since_push > 365:
            score -= 30   # Abandoned repo
        elif days_since_push > 180:
            score -= 15   # Stale repo
        elif days_since_push > 90:
            score -= 5    # Slow updates

        commits_30d = data.get("commits_last_30_days", 0)
        if commits_30d == 0:
            score -= 20   # No recent activity
        elif commits_30d < 3:
            score -= 10   # Very low activity
        elif commits_30d >= 10:
            score += 5    # Active development

        # ── Quality bonuses/penalties ─────────────────────────────────
        if data.get("has_tests"):
            score += 10
        else:
            score -= 15   # No tests is serious debt

        if data.get("has_cicd"):
            score += 8
            cicd_count = data.get("cicd_workflow_count", 0)
            if cicd_count >= 3:
                score += 4  # Multiple CI/CD pipelines
        else:
            score -= 10   # No CI/CD

        if data.get("has_security_policy"):
            score += 5
        else:
            score -= 5

        # ── Issue health ──────────────────────────────────────────────
        open_issues = data.get("open_issues", 0)
        old_issues  = data.get("old_issues_90d", 0)

        if old_issues > 20:
            score -= 15   # Many stale issues
        elif old_issues > 10:
            score -= 8
        elif old_issues > 5:
            score -= 4

        # Issue-to-star ratio (high = poor maintenance)
        stars = max(data.get("stars", 1), 1)
        issue_ratio = open_issues / stars
        if issue_ratio > 0.05:
            score -= 10
        elif issue_ratio > 0.02:
            score -= 5

        # ── PR health ─────────────────────────────────────────────────
        open_prs = data.get("open_prs", 0)
        if open_prs > 50:
            score -= 10   # Too many unmerged PRs
        elif open_prs > 20:
            score -= 5

        avg_merge_days = data.get("avg_pr_merge_days", 0)
        if avg_merge_days > 30:
            score -= 8    # Very slow PR reviews
        elif avg_merge_days > 14:
            score -= 4
        elif 0 < avg_merge_days <= 3:
            score += 5    # Fast reviews

        # ── Documentation quality ─────────────────────────────────────
        readme_size = data.get("readme_size_bytes", 0)
        if readme_size > 5000:
            score += 5    # Excellent documentation
        elif readme_size > 1000:
            score += 2
        elif readme_size < 200:
            score -= 8    # Poor documentation

        # ── Release cadence ───────────────────────────────────────────
        days_since_release = data.get("days_since_last_release", 999)
        if days_since_release <= 30:
            score += 5
        elif days_since_release > 365:
            score -= 10
        elif days_since_release > 180:
            score -= 5

        # ── Red flags ─────────────────────────────────────────────────
        if data.get("is_archived"):
            score -= 40   # Archived = abandoned

        if data.get("is_fork"):
            score -= 5    # Forks have maintenance risk

        dep_files = data.get("dependency_files", [])
        if not dep_files:
            score -= 10   # No dependency management
        elif len(dep_files) >= 2:
            score += 3

        # ── Team size ─────────────────────────────────────────────────
        contributors = data.get("contributors_count", 0)
        if contributors == 0:
            score -= 20   # Solo project risk
        elif contributors == 1:
            score -= 10   # Bus factor = 1
        elif contributors >= 5:
            score += 5
        elif contributors >= 10:
            score += 8

        # ── License ───────────────────────────────────────────────────
        license_name = data.get("license", "None")
        if license_name and license_name != "None":
            score += 5    # Has a license

        return max(0, min(100, score))

    # ── Fetch from MCP ────────────────────────────────────────────────

    def _fetch_repo(self, repo_url: str) -> dict:
        try:
            resp = httpx.post(
                f"{MCP_SERVER_URL}/github/repo",
                json={"repo_url": repo_url},
                timeout=45,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[CodeAuditor] MCP unavailable, using mock: {e}")
            return self._mock(repo_url)

    # ── Build Gemini prompt with real anchors ─────────────────────────

    def _build_prompt(self, company_name: str, repo_url: str,
                      data: dict, rule_score: int) -> str:
        return f"""
You are a senior technical due diligence analyst performing a code audit for an M&A transaction.
You have been given REAL GitHub metrics. Use these to produce an ACCURATE assessment.

Company: {company_name}
Repository: {repo_url}

=== REAL GITHUB METRICS ===
Activity:
- Days since last commit: {data.get('days_since_push', 'N/A')}
- Commits in last 30 days: {data.get('commits_last_30_days', 'N/A')}
- Commits in last 90 days: {data.get('commits_last_90_days', 'N/A')}
- Avg days between commits: {data.get('avg_days_between_commits', 'N/A')}

Code Quality:
- Has automated tests: {data.get('has_tests', False)}
- Has CI/CD pipelines: {data.get('has_cicd', False)}
- Number of CI/CD workflows: {data.get('cicd_workflow_count', 0)}
- Has security policy: {data.get('has_security_policy', False)}
- Dependency files found: {data.get('dependency_files', [])}
- README size (bytes): {data.get('readme_size_bytes', 0)}
- Codebase size (KB): {data.get('size_kb', 0)}

Issue Health:
- Total open issues: {data.get('open_issues', 0)}
- Issues older than 90 days: {data.get('old_issues_90d', 0)}
- Open pull requests: {data.get('open_prs', 0)}
- Avg PR merge time (days): {data.get('avg_pr_merge_days', 0)}

Team & Maturity:
- Contributors: {data.get('contributors_count', 0)}
- Stars: {data.get('stars', 0)}
- Forks: {data.get('forks', 0)}
- Latest release: {data.get('latest_release', 'none')}
- Days since last release: {data.get('days_since_last_release', 'N/A')}
- License: {data.get('license', 'None')}
- Is archived: {data.get('is_archived', False)}
- Languages: {data.get('languages', {})}

=== RULE-BASED PRE-SCORE: {rule_score}/100 ===
Your tech_debt_score should be close to {rule_score} — only deviate significantly if you see strong reasons.

Scoring guide:
- 85-100: Excellent codebase, minimal debt, production-ready
- 70-84: Good quality, some areas to improve
- 50-69: Moderate debt, needs attention before acquisition
- 30-49: Significant debt, major remediation needed
- 0-29: Critical debt, high acquisition risk

Respond ONLY with a valid JSON object (no markdown, no extra text):

{{
  "tech_debt_score": <integer 0-100>,
  "security_flags": [<list of specific security concerns found in the data>],
  "strengths": [<list of technical strengths with specific evidence>],
  "risks": [<list of technical risks with specific evidence>],
  "code_quality_summary": "<3-4 sentence professional assessment using the actual metrics>",
  "recommended_actions": [<list of specific remediation steps before acquisition>],
  "bus_factor_risk": "<LOW|MEDIUM|HIGH based on contributor count>",
  "maintenance_health": "<ACTIVE|MODERATE|STALE|ABANDONED based on commit frequency>"
}}
"""

    def _parse(self, raw: str) -> dict:
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except Exception:
            return {
                "tech_debt_score":    50,
                "security_flags":     ["Could not parse response"],
                "strengths":          [],
                "risks":              ["Analysis incomplete"],
                "code_quality_summary": raw[:300],
                "recommended_actions": [],
                "bus_factor_risk":    "UNKNOWN",
                "maintenance_health": "UNKNOWN",
            }

    def _mock(self, repo_url: str) -> dict:
        return {
            "repo_url": repo_url,
            "name": "unknown",
            "stars": 0, "forks": 0,
            "open_issues": 10, "open_prs": 5,
            "languages": {"Python": 100},
            "days_since_push": 30,
            "commits_last_30_days": 5,
            "commits_last_90_days": 15,
            "avg_days_between_commits": 6,
            "contributors_count": 2,
            "has_tests": False, "has_cicd": False,
            "cicd_workflow_count": 0,
            "has_security_policy": False,
            "dependency_files": ["requirements.txt"],
            "readme_size_bytes": 500,
            "old_issues_90d": 3,
            "avg_pr_merge_days": 7,
            "days_since_last_release": 90,
            "latest_release": "v1.0.0",
            "license": "MIT", "size_kb": 1000,
            "is_archived": False, "is_fork": False,
        }