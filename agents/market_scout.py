"""
VEDA — Sub-Agent 3: Market Scout (Async)
"""

import json
from agents.schemas import MarketScoutResult
from utils.vertex_helper import ask_gemini_async

class MarketScoutAgent:

    async def run(self, job_id: str, company_name: str, industry: str, description: str = "") -> dict:
        print(f"[MarketScout] Researching competitors for {company_name}")

        prompt = f"""
        You are a market intelligence researcher.
        Company: {company_name}
        Industry: {industry}
        Description: {description}
        Identify competitors and perform SWOT analysis.
        """
        raw_analysis = await ask_gemini_async(prompt, response_schema=MarketScoutResult.model_json_schema())
        result = json.loads(raw_analysis)
        result["job_id"] = job_id
        return result
