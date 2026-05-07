"""
VEDA — Sub-Agent 4: Financial Analyst (Async)
"""

import json
import httpx
from agents.schemas import FinancialResult
from utils.vertex_helper import ask_gemini_async
from utils.config import MCP_SERVER_URL

class FinancialAnalystAgent:

    async def run(self, job_id: str, company_name: str, industry: str) -> dict:
        print(f"[FinancialAnalyst] Analyzing financials for {company_name}")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{MCP_SERVER_URL}/financials/simulated", params={"company_name": company_name, "industry": industry}, timeout=15)
                financial_data = resp.json().get("metrics", {})
        except Exception as e:
            print(f"[FinancialAnalyst] MCP failed: {e}")
            financial_data = {}

        prompt = f"""
        You are a private equity financial analyst.
        Company: {company_name}
        Data: {json.dumps(financial_data, indent=2)}
        Assess financial health and valuation.
        """
        raw_analysis = await ask_gemini_async(prompt, response_schema=FinancialResult.model_json_schema())
        result = json.loads(raw_analysis)
        result["job_id"] = job_id
        return result
