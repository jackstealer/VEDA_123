"""
VEDA — Sub-Agent 2: Regulatory Scout
Grounds compliance checks with real Indian legal documents via Vertex AI Search (RAG).
"""
import json
import logging
import re
from utils.vertex_helper import ask_gemini
from utils.vertex_search import search_regulatory_context

logger = logging.getLogger(__name__)

COMPLIANCE_FRAMEWORKS = {
    "fintech": {
        "regulations": [
            "RBI Digital Lending Guidelines 2022",
            "SEBI LODR Regulations",
            "Prevention of Money Laundering Act (PMLA)",
            "Payment and Settlement Systems Act 2007",
            "RBI Master Directions on KYC",
            "FEMA Regulations",
            "Consumer Protection Act 2019",
        ],
        "critical_checks": [
            "RBI/SEBI registration or license status",
            "KYC/AML compliance program",
            "Data localisation compliance (RBI)",
            "Escrow account maintenance",
            "Grievance redressal mechanism",
            "Interest rate disclosure norms",
        ],
        "red_flag_triggers": [
            "Operating without RBI/SEBI license",
            "Missing KYC process",
            "No escrow account",
            "PMLA violations",
            "Data stored outside India",
        ],
        "base_risk": "HIGH",
    },
    "healthtech": {
        "regulations": [
            "Digital Information Security in Healthcare Act (DISHA)",
            "IT Act 2000 – Data Privacy Sections",
            "CDSCO Medical Device Rules 2017",
            "Telemedicine Practice Guidelines 2020",
            "Clinical Establishments Act",
        ],
        "critical_checks": [
            "DISHA compliance for patient data",
            "Telemedicine platform registration",
            "Doctor verification process",
            "Data encryption for health records",
            "Consent management system",
        ],
        "red_flag_triggers": [
            "Storing health data without encryption",
            "No doctor verification",
            "Unapproved medical devices",
            "Missing consent framework",
        ],
        "base_risk": "HIGH",
    },
    "edtech": {
        "regulations": [
            "National Education Policy 2020",
            "PDPB 2023 (Children's data)",
            "Consumer Protection (E-Commerce) Rules 2020",
            "UGC regulations (if degree programs)",
        ],
        "critical_checks": [
            "PDPB compliance for under-18 users",
            "UGC recognition (if degrees offered)",
            "Refund policy compliance",
            "Data retention policies",
        ],
        "red_flag_triggers": [
            "Collecting children's data without parental consent",
            "Offering degrees without UGC recognition",
            "No refund mechanism",
        ],
        "base_risk": "MEDIUM",
    },
    "saas": {
        "regulations": [
            "IT Act 2000 Section 43A",
            "PDPB 2023 Obligations",
            "GST Act (SaaS taxation)",
            "Consumer Protection Act 2019",
            "Companies Act 2013",
        ],
        "critical_checks": [
            "PDPB data processing agreement",
            "GST registration and compliance",
            "Data breach notification process",
            "Cross-border data transfer mechanisms",
            "SOC2/ISO27001 certification status",
        ],
        "red_flag_triggers": [
            "No privacy policy",
            "No data processing agreement",
            "Missing GST registration",
            "No security certifications",
        ],
        "base_risk": "MEDIUM",
    },
    "ecommerce": {
        "regulations": [
            "Consumer Protection (E-Commerce) Rules 2020",
            "IT Act 2000",
            "PDPB 2023",
            "GST Act",
            "FDI Policy for e-commerce",
        ],
        "critical_checks": [
            "Seller verification process",
            "Grievance officer appointment",
            "Return/refund policy compliance",
            "FDI compliance",
            "GST TCS compliance",
        ],
        "red_flag_triggers": [
            "FDI violations",
            "No grievance officer",
            "Missing GST TCS compliance",
        ],
        "base_risk": "MEDIUM",
    },
    "deeptech": {
        "regulations": [
            "IT Act 2000",
            "PDPB 2023",
            "Patents Act 1970",
            "Export Control Regulations (SCOMET)",
            "Companies Act 2013",
        ],
        "critical_checks": [
            "IP ownership clarity",
            "Export control compliance",
            "Patent filing status",
            "Academic IP assignment agreements",
        ],
        "red_flag_triggers": [
            "Unclear IP ownership",
            "Export control violations",
            "No patent protection",
        ],
        "base_risk": "LOW",
    },
    "default": {
        "regulations": [
            "Companies Act 2013",
            "PDPB 2023",
            "IT Act 2000",
            "GST Act",
            "Labour Laws (PF, ESI, Gratuity)",
        ],
        "critical_checks": [
            "Company registration and ROC filings",
            "GST registration",
            "Labour law compliance",
            "Data privacy policy",
            "IP ownership agreements",
        ],
        "red_flag_triggers": [
            "ROC filing defaults",
            "GST non-compliance",
            "Labour law violations",
        ],
        "base_risk": "LOW",
    },
}


class RegulatoryScoutAgent:

    def run(
        self,
        job_id: str,
        company_name: str,
        industry: str,
        description: str = "",
    ) -> dict:
        logger.info("[RegulatoryScout] Checking: %s (%s)", company_name, industry)

        framework = self._get_framework(industry)

        # ── RAG: fetch grounded legal context from Vertex AI Search ──
        rag_context = search_regulatory_context(
            query=f"{company_name} {industry} compliance requirements",
            industry=industry,
        )
        if rag_context:
            logger.info("[RegulatoryScout] RAG context retrieved (%d chars)", len(rag_context))
        else:
            logger.info("[RegulatoryScout] No RAG context — using framework only")

        prompt = self._build_prompt(
            company_name, industry, description, framework, rag_context
        )
        raw    = ask_gemini(prompt, context="RegulatoryScout")
        result = self._parse(raw)

        result["applicable_regulations"] = framework["regulations"]
        result["critical_checks"]        = framework["critical_checks"]
        result["industry_base_risk"]     = framework["base_risk"]
        result["rag_grounded"]           = bool(rag_context)
        result["job_id"]                 = job_id

        logger.info(
            "[RegulatoryScout] Compliance score: %s | RAG grounded: %s",
            result.get("compliance_score"), result.get("rag_grounded"),
        )
        return result

    def _get_framework(self, industry: str) -> dict:
        key = industry.lower().replace(" ", "").replace("-", "")
        for k in COMPLIANCE_FRAMEWORKS:
            if k in key:
                return COMPLIANCE_FRAMEWORKS[k]
        return COMPLIANCE_FRAMEWORKS["default"]

    def _build_prompt(
        self,
        company_name: str,
        industry: str,
        description: str,
        framework: dict,
        rag_context: str,
    ) -> str:
        regs   = "\n".join(f"  • {r}" for r in framework["regulations"])
        checks = "\n".join(f"  • {c}" for c in framework["critical_checks"])
        flags  = "\n".join(f"  • {f}" for f in framework["red_flag_triggers"])

        rag_section = (
            f"\n=== GROUNDED LEGAL CONTEXT (from Vertex AI Search) ===\n{rag_context}\n"
            if rag_context
            else "\n=== NO RAG CONTEXT AVAILABLE — use framework knowledge only ===\n"
        )

        return f"""
You are a regulatory compliance specialist performing M&A due diligence in India.
You are assessing a {industry} company for acquisition.

Company: {company_name}
Industry: {industry}
Industry Risk Level: {framework["base_risk"]}
Description: {description or "Not provided"}

=== APPLICABLE REGULATIONS ===
{regs}

=== CRITICAL COMPLIANCE CHECKS ===
{checks}

=== RED FLAG TRIGGERS ===
{flags}
{rag_section}
Use the grounded legal context above (if available) to make your assessment more accurate.
Cite specific regulation names, section numbers, and penalty amounts where possible.

Scoring guide:
- 85-100: Fully compliant, all licenses in place, low regulatory risk
- 70-84: Mostly compliant, minor gaps easily remediated
- 50-69: Significant gaps, 3-6 months to fix, some deal risk
- 30-49: Major violations, regulatory action risk, high deal risk
- 0-29: Critical violations, deal-breaking regulatory issues

Respond ONLY with valid JSON (no markdown):

{{
  "compliance_score": <integer 0-100>,
  "regulatory_risks": [<specific risks with regulation names and penalty amounts>],
  "compliant_areas": [<areas likely compliant>],
  "red_flags": [<deal-blocking issues>],
  "compliance_summary": "<3-4 sentences citing specific regulations and penalties>",
  "due_diligence_recommendations": [<specific documents to request>],
  "estimated_remediation_time": "<e.g. 1-2 months>",
  "regulatory_deal_blocker": <true|false>
}}
"""

    def _parse(self, raw: str) -> dict:
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except Exception:
            logger.warning("[RegulatoryScout] JSON parse failed")
            return {
                "compliance_score":               50,
                "regulatory_risks":               ["Could not parse response"],
                "compliant_areas":                [],
                "red_flags":                      [],
                "compliance_summary":             raw[:300],
                "due_diligence_recommendations":  [],
                "estimated_remediation_time":     "Unknown",
                "regulatory_deal_blocker":        False,
            }
