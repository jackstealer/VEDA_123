"""
VEDA — Sub-Agent 6: News Sentiment Analyst
Searches real-time news about the target company using Vertex AI grounding.
Produces a Market Perception Score based on news sentiment.
"""
import json
import logging
import re
from datetime import datetime
from utils.vertex_helper import ask_gemini

logger = logging.getLogger(__name__)


class NewsSentimentAgent:

    def run(
        self,
        job_id: str,
        company_name: str,
        industry: str,
        github_repo_url: str = "",
    ) -> dict:
        logger.info("[NewsSentiment] Analysing news for: %s", company_name)

        # ── Step 1: Search for recent news via Gemini grounding ───────
        news_data = self._fetch_news_sentiment(company_name, industry)

        # ── Step 2: Score and structure ───────────────────────────────
        result = self._parse(news_data)
        result["job_id"]       = job_id
        result["company_name"] = company_name
        result["analysed_at"]  = datetime.utcnow().isoformat()

        logger.info(
            "[NewsSentiment] Market Perception Score: %s | Sentiment: %s",
            result.get("market_perception_score"),
            result.get("overall_sentiment"),
        )
        return result

    def _fetch_news_sentiment(self, company_name: str, industry: str) -> str:
        prompt = f"""
You are a financial news analyst performing M&A due diligence.
Search your knowledge for recent news, developments, controversies, and market perception
about the following company in the past 12 months.

Company: {company_name}
Industry: {industry}

Analyse the following dimensions:
1. Recent funding rounds or financial health signals
2. Product launches or major announcements
3. Controversies, legal issues, regulatory actions
4. Leadership changes (CEO, CTO departures)
5. Customer wins or losses (major partnerships or churns)
6. Media sentiment (positive/negative coverage trends)
7. Competitive threats mentioned in news
8. Any M&A rumours or previous acquisition attempts

Scoring guide for Market Perception Score:
- 85-100: Excellent — positive news, strong growth signals, no controversies
- 70-84: Good — mostly positive, minor issues
- 50-69: Neutral — mixed signals, some concerns
- 30-49: Negative — significant controversies or financial concerns
- 0-29: Critical — major scandals, regulatory action, or business failure signals

Respond ONLY with valid JSON (no markdown):

{{
  "market_perception_score": <integer 0-100>,
  "overall_sentiment": "<VERY POSITIVE | POSITIVE | NEUTRAL | NEGATIVE | VERY NEGATIVE>",
  "recent_developments": [
    {{
      "title": "<news headline or development>",
      "sentiment": "<POSITIVE | NEUTRAL | NEGATIVE>",
      "impact": "<HIGH | MEDIUM | LOW>",
      "date_approximate": "<e.g. Q1 2025 or Recent>"
    }}
  ],
  "funding_status": "<e.g. Series C funded | Bootstrapped | IPO filed | Unknown>",
  "controversy_flags": [<list of specific controversies or empty list>],
  "leadership_stability": "<STABLE | RECENT CHANGES | UNSTABLE | UNKNOWN>",
  "media_coverage_trend": "<INCREASING | STABLE | DECREASING>",
  "key_risks_from_news": [<list of M&A risks identified from news>],
  "key_positives_from_news": [<list of positives identified from news>],
  "sentiment_summary": "<3-4 sentence professional summary of market perception for M&A board>",
  "data_confidence": "<HIGH | MEDIUM | LOW — based on how much you know about this company>"
}}
"""
        return ask_gemini(prompt, temperature=0.3, context="NewsSentiment")

    def _parse(self, raw: str) -> dict:
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except Exception:
            logger.warning("[NewsSentiment] JSON parse failed")
            return {
                "market_perception_score": 50,
                "overall_sentiment":       "NEUTRAL",
                "recent_developments":     [],
                "funding_status":          "Unknown",
                "controversy_flags":       [],
                "leadership_stability":    "UNKNOWN",
                "media_coverage_trend":    "STABLE",
                "key_risks_from_news":     [],
                "key_positives_from_news": [],
                "sentiment_summary":       raw[:300],
                "data_confidence":         "LOW",
            }
