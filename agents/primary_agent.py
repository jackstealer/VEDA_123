"""
VEDA — Primary Orchestrator Agent
Coordinates 4 sub-agents + Competitor Intelligence with per-agent timeouts.
"""
import asyncio
import logging
import traceback
from datetime import datetime, timedelta

import vertexai
from vertexai.generative_models import GenerativeModel

from agents.code_auditor import CodeAuditorAgent
from agents.regulatory_scout import RegulatoryScoutAgent
from agents.market_analyst import MarketAnalystAgent
from agents.executive_summary import ExecutiveSummaryAgent
from agents.competitor_intelligence import CompetitorIntelligenceAgent
from agents.news_sentiment import NewsSentimentAgent
from db.bigquery_client import BigQueryClient
from utils.config import (
    PROJECT_ID, LOCATION, MCP_SERVER_URL,
    AGENT_TIMEOUT_CODE, AGENT_TIMEOUT_REGULATORY,
    AGENT_TIMEOUT_MARKET, AGENT_TIMEOUT_SUMMARY,
)

logger = logging.getLogger(__name__)
from utils.cloud_logger import log_audit_event


class PrimaryAgent:

    def __init__(self, progress_manager=None):
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        self.model            = GenerativeModel("gemini-2.5-flash")
        self.bq               = BigQueryClient()
        self.progress         = progress_manager
        self.code_auditor     = CodeAuditorAgent()
        self.reg_scout        = RegulatoryScoutAgent()
        self.market_analyst   = MarketAnalystAgent()
        self.exec_summary     = ExecutiveSummaryAgent()
        self.competitor_intel = CompetitorIntelligenceAgent()
        self.news_sentiment   = NewsSentimentAgent()

    def run_full_audit(
        self,
        job_id: str,
        company_name: str,
        github_repo_url: str,
        industry: str,
        description: str = "",
        schedule_meeting: bool = False,
        attendee_email: str = "",
        user_access_token: str = "",
        refresh_token: str = "",
    ) -> None:
        asyncio.run(self._orchestrate(
            job_id, company_name, github_repo_url,
            industry, description, schedule_meeting,
            attendee_email, user_access_token, refresh_token,
        ))

    async def _orchestrate(
        self,
        job_id: str,
        company_name: str,
        github_repo_url: str,
        industry: str,
        description: str,
        schedule_meeting: bool,
        attendee_email: str,
        user_access_token: str = "",
        refresh_token: str = "",
    ) -> None:
        logger.info("[PrimaryAgent] Starting audit %s — %s", job_id, company_name)

        try:
            self.bq.update_job_status(job_id, "RUNNING", "Audit started")
            await self._create_tasks_checklist(
                company_name, industry, user_access_token, refresh_token
            )

            # ── Agent 1: Code Audit ───────────────────────────────────
            await self.progress.agent_started(
                job_id, 1, "Code Auditor",
                f"🔍 Scanning repository: {github_repo_url}",
            )
            self.bq.log_agent_event(job_id, 1, "Code Auditor", "RUNNING",
                f"Scanning {github_repo_url}", 0)

            code_results = await self._run_with_timeout(
                self.code_auditor.run, AGENT_TIMEOUT_CODE,
                job_id, github_repo_url, company_name,
            )
            await self.progress.agent_completed(
                job_id, 1, "Code Auditor",
                f"✅ Tech Debt Score: {code_results.get('tech_debt_score')}/100",
                data={
                    "tech_debt_score":    code_results.get("tech_debt_score"),
                    "security_flags":     code_results.get("security_flags", []),
                    "maintenance_health": code_results.get("maintenance_health", ""),
                    "bus_factor_risk":    code_results.get("bus_factor_risk", ""),
                    "summary":            code_results.get("code_quality_summary", ""),
                },
            )
            self.bq.log_agent_event(job_id, 1, "Code Auditor", "DONE",
                f"Score: {code_results.get('tech_debt_score')}", 25, code_results)

            # ── Agent 2: Regulatory ───────────────────────────────────
            await self.progress.agent_started(
                job_id, 2, "Regulatory Scout",
                f"📋 Checking {industry} compliance frameworks...",
            )
            self.bq.log_agent_event(job_id, 2, "Regulatory Scout", "RUNNING",
                f"Compliance check: {industry}", 25)

            reg_results = await self._run_with_timeout(
                self.reg_scout.run, AGENT_TIMEOUT_REGULATORY,
                job_id, company_name, industry, description,
            )
            await self.progress.agent_completed(
                job_id, 2, "Regulatory Scout",
                f"✅ Compliance Score: {reg_results.get('compliance_score')}/100",
                data={
                    "compliance_score":        reg_results.get("compliance_score"),
                    "red_flags":               reg_results.get("red_flags", []),
                    "regulatory_deal_blocker": reg_results.get("regulatory_deal_blocker", False),
                    "estimated_remediation":   reg_results.get("estimated_remediation_time", ""),
                    "summary":                 reg_results.get("compliance_summary", ""),
                },
            )
            self.bq.log_agent_event(job_id, 2, "Regulatory Scout", "DONE",
                f"Score: {reg_results.get('compliance_score')}", 50, reg_results)

            # ── Agent 3: Market Forecast ──────────────────────────────
            await self.progress.agent_started(
                job_id, 3, "Market Analyst",
                "📈 Running Bear / Base / Bull 3-year simulation...",
            )
            self.bq.log_agent_event(job_id, 3, "Market Analyst", "RUNNING",
                "3-year forecast simulation", 50)

            market_results = await self._run_with_timeout(
                self.market_analyst.run, AGENT_TIMEOUT_MARKET,
                job_id, company_name, industry,
                code_results["tech_debt_score"],
                reg_results["compliance_score"],
                code_results.get("raw_github_data", {}),
            )
            await self.progress.agent_completed(
                job_id, 3, "Market Analyst",
                f"✅ Market Fit: {market_results.get('market_fit_score')}/100",
                data={
                    "market_fit_score": market_results.get("market_fit_score"),
                    "price_range":      market_results.get("recommended_acquisition_price_range_inr_cr"),
                    "summary":          market_results.get("forecast_summary", ""),
                },
            )
            self.bq.log_agent_event(job_id, 3, "Market Analyst", "DONE",
                f"Market fit: {market_results.get('market_fit_score')}", 75, market_results)

            # ── Agent 4: Executive Summary ────────────────────────────
            await self.progress.agent_started(
                job_id, 4, "Executive Summary",
                "📝 Synthesising board-level recommendation...",
            )
            self.bq.log_agent_event(job_id, 4, "Executive Summary", "RUNNING",
                "Generating executive report", 75)

            summary_results = await self._run_with_timeout(
                self.exec_summary.run, AGENT_TIMEOUT_SUMMARY,
                job_id, company_name, code_results, reg_results, market_results,
            )

            if schedule_meeting and attendee_email:
                await self._schedule_kickoff(
                    job_id, company_name, attendee_email,
                    user_access_token, refresh_token,
                )

            overall_risk = summary_results.get("composite_score") or round(
                code_results["tech_debt_score"] * 0.35 +
                reg_results["compliance_score"] * 0.35 +
                market_results.get("market_fit_score", 50) * 0.30, 1,
            )

            # ── Agent 6: News Sentiment (non-blocking) ─────────────
            news_results = await self._run_news_sentiment(
                job_id, company_name, industry, github_repo_url,
            )

            # ── Agent 5: Competitor Intelligence (non-blocking) ───────
            competitor_results = await self._run_competitor_intelligence(
                job_id, company_name, industry, github_repo_url,
                code_results, reg_results, market_results,
            )

            report = {
                "job_id":                  job_id,
                "company_name":            company_name,
                "github_repo_url":         github_repo_url,
                "industry":                industry,
                "overall_risk_score":      overall_risk,
                "code_audit":              code_results,
                "regulatory":              reg_results,
                "market_forecast":         market_results,
                "executive_summary":       summary_results,
                "competitor_intelligence": competitor_results,
                "news_sentiment":          news_results,
                "completed_at":            datetime.utcnow().isoformat(),
                "deal_intelligence":       await self._compute_deal_intelligence(
                    job_id, summary_results, code_results, reg_results, market_results
                ),
            }

            self.bq.save_report(job_id, report)
            self.bq.update_job_status(job_id, "COMPLETED", "Audit complete")
            self.bq.log_agent_event(job_id, 4, "Executive Summary", "DONE",
                f"Verdict: {summary_results.get('one_line_verdict', '')}", 100, summary_results)

            await self.progress.agent_completed(
                job_id, 4, "Executive Summary",
                f"✅ {summary_results.get('recommendation')} — {summary_results.get('overall_rating')}",
                data={
                    "recommendation":   summary_results.get("recommendation"),
                    "overall_rating":   summary_results.get("overall_rating"),
                    "one_line_verdict": summary_results.get("one_line_verdict"),
                },
            )
            await self.progress.audit_completed(job_id, {
                "overall_risk_score": overall_risk,
                "recommendation":     summary_results.get("recommendation"),
                "overall_rating":     summary_results.get("overall_rating"),
                "one_line_verdict":   summary_results.get("one_line_verdict"),
                "report_url":         f"/report/{job_id}",
                "pdf_url":            f"/report/{job_id}/pdf",
            })
            logger.info("[PrimaryAgent] Audit %s complete — %s",
                        job_id, summary_results.get("recommendation"))

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("[PrimaryAgent] Audit %s failed: %s\n%s", job_id, exc, tb)
            self.bq.update_job_status(job_id, "FAILED", str(exc))
            self.bq.log_error(job_id, error=exc, traceback_str=tb)
            await self.progress.audit_failed(job_id, str(exc))
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _run_with_timeout(self, fn, timeout: int, *args):
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, fn, *args),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"{fn.__self__.__class__.__name__} timed out after {timeout}s"
            )

    async def _run_competitor_intelligence(
        self, job_id, company_name, industry,
        github_repo_url, code_results, reg_results, market_results,
    ) -> dict:
        try:
            target_scores = {
                "tech_debt_score":  code_results.get("tech_debt_score"),
                "compliance_score": reg_results.get("compliance_score"),
                "market_fit_score": market_results.get("market_fit_score"),
            }
            return await self._run_with_timeout(
                self.competitor_intel.run, 120,
                job_id, company_name, industry,
                github_repo_url, target_scores,
            )
        except Exception as exc:
            logger.warning("[PrimaryAgent] Competitor intel failed (non-fatal): %s", exc)
            return {}

    async def _create_tasks_checklist(
        self, company_name: str, industry: str,
        user_access_token: str = "", refresh_token: str = "",
    ) -> None:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{MCP_SERVER_URL}/tasks/create_checklist",
                    params={
                        "company_name":      company_name,
                        "industry":          industry,
                        "user_access_token": user_access_token,
                        "refresh_token":     refresh_token,
                    },
                    timeout=15,
                )
                data = resp.json()
                logger.info("[PrimaryAgent] Tasks created: %d | Calendar synced: %s",
                            data.get("tasks_created", 0), data.get("calendar_synced", False))
        except Exception as exc:
            logger.warning("[PrimaryAgent] Tasks checklist failed (non-fatal): %s", exc)

    async def _schedule_kickoff(
        self, job_id: str, company_name: str, attendee_email: str,
        user_access_token: str = "", refresh_token: str = "",
    ) -> None:
        import httpx
        start = datetime.utcnow() + timedelta(days=1)
        end   = start + timedelta(hours=1)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{MCP_SERVER_URL}/calendar/schedule",
                    json={
                        "summary":           f"VEDA Due Diligence Kickoff — {company_name}",
                        "start_datetime":    start.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                        "end_datetime":      end.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                        "description":       f"VEDA M&A kickoff — {company_name} | Job: {job_id}",
                        "user_access_token": user_access_token,
                        "refresh_token":     refresh_token,
                    },
                    timeout=15,
                )
                data = resp.json()
                logger.info("[PrimaryAgent] Kickoff scheduled: %s", data.get("event_id"))
        except Exception as exc:
            logger.warning("[PrimaryAgent] Calendar scheduling failed (non-fatal): %s", exc)

    async def _run_news_sentiment(
        self,
        job_id: str,
        company_name: str,
        industry: str,
        github_repo_url: str,
    ) -> dict:
        """Run news sentiment as non-blocking background enrichment."""
        try:
            return await self._run_with_timeout(
                self.news_sentiment.run,
                90,
                job_id, company_name, industry, github_repo_url,
            )
        except Exception as exc:
            logger.warning("[PrimaryAgent] News sentiment failed (non-fatal): %s", exc)
            return {}

    async def _compute_deal_intelligence(
        self, job_id, summary_results, code_results, reg_results, market_results
    ) -> dict:
        """Compute deal intelligence — sentiment, investment score, embeddings."""
        try:
            from utils.sentiment_engine  import analyze_sentiment
            from utils.investment_scorer import compute_investment_score
            from utils.embeddings_engine import store_startup_embedding

            summary_text = summary_results.get("executive_summary", "") or \
                           summary_results.get("one_line_verdict", "")

            sentiment = analyze_sentiment(summary_text) if summary_text else \
                        {"score": 0, "magnitude": 0, "label": "NEUTRAL"}

            investment = compute_investment_score(
                tech_debt_score     = code_results.get("tech_debt_score", 50),
                compliance_score    = reg_results.get("compliance_score", 50),
                market_fit_score    = market_results.get("market_fit_score", 50),
                sentiment_score     = sentiment["score"],
                sentiment_magnitude = sentiment["magnitude"],
                pitch_text          = summary_text,
            )

            # Store embedding for future similarity search (non-blocking)
            asyncio.get_event_loop().run_in_executor(None, store_startup_embedding,
                job_id,
                summary_results.get("job_id", job_id),
                "unknown",
                summary_text,
                {"tech": code_results.get("tech_debt_score"),
                 "compliance": reg_results.get("compliance_score"),
                 "market": market_results.get("market_fit_score")},
            )

            logger.info("[PrimaryAgent] Deal intelligence: score=%d grade=%s",
                investment["investment_score"], investment["grade"])
            return {"sentiment": sentiment, **investment}

        except Exception as exc:
            logger.warning("[PrimaryAgent] Deal intelligence failed (non-fatal): %s", exc)
            return {}
