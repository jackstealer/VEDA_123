"""
VEDA — Document AI Pitch Deck Parser
Extracts structured startup data from uploaded PDF pitch decks.
Uses Google Cloud Document AI OCR + heuristic field extraction.
"""
import logging
import re
from typing import Optional
from utils.config import PROJECT_ID

logger = logging.getLogger(__name__)

# Document AI processor — uses pre-trained OCR processor
import os
_PROCESSOR_ID = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
_PROCESSOR_REGION = "us"

import os

def parse_pitch_deck(pdf_bytes: bytes) -> dict:
    """
import os
import re
import logging
from typing import Optional
from utils.config import PROJECT_ID

    Extract structured data from a PDF pitch deck.
    Returns company name, industry, financials, problem/solution.
    """
    try:
        raw_text = _extract_text_document_ai(pdf_bytes)
    except Exception as exc:
        logger.warning("[PitchDeck] Document AI failed: %s — using fallback", exc)
        raw_text = _extract_text_fallback(pdf_bytes)

    if not raw_text:
        return _empty_extraction()

    extracted = _parse_fields(raw_text)
    logger.info(
        "[PitchDeck] Extracted: company=%s industry=%s",
        extracted.get("company_name"), extracted.get("industry"),
    )
    return extracted


def _extract_text_document_ai(pdf_bytes: bytes) -> str:
    """Use Document AI OCR to extract text from PDF."""
    from google.cloud import documentai_v1 as documentai

    client   = documentai.DocumentProcessorServiceClient()
    name     = f"projects/{PROJECT_ID}/locations/{_PROCESSOR_REGION}/processors/{_PROCESSOR_ID}"

    raw_doc = documentai.RawDocument(
        content=pdf_bytes,
        mime_type="application/pdf",
    )
    request  = documentai.ProcessRequest(name=name, raw_document=raw_doc)
    result   = client.process_document(request=request)
    return result.document.text


def _extract_text_fallback(pdf_bytes: bytes) -> str:
    """Fallback: extract text using pypdf if Document AI unavailable."""
    try:
        import io
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning("[PitchDeck] pypdf fallback failed: %s", exc)
        return ""


def _parse_fields(text: str) -> dict:
    """Extract structured fields from raw text using heuristics."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    return {
        "company_name":          _extract_company_name(text, lines),
        "industry":              _extract_industry(text),
        "description":           _extract_section(text, ["solution", "product", "platform"]),
        "problem":               _extract_section(text, ["problem", "challenge", "pain point"]),
        "solution":              _extract_section(text, ["solution", "product", "platform"]),
        "revenue_inr_lakhs":     _extract_revenue(text),
        "growth_rate_pct":       _extract_growth_rate(text),
        "team_size":             _extract_team_size(text),
        "funding_stage":         _extract_funding_stage(text),
        "target_market":         _extract_section(text, ["market", "tam", "addressable"]),
        "github_url":            _extract_github_url(text),
        "raw_text_preview":      text[:500],
        "extraction_confidence": _estimate_confidence(text),
    }


def _extract_company_name(text: str, lines: list) -> str:
    # First non-empty line is often the company name
    for line in lines[:5]:
        if 2 <= len(line.split()) <= 5 and not any(
            kw in line.lower() for kw in ["pitch", "deck", "presentation", "confidential"]
        ):
            return line
    return ""


def _extract_industry(text: str) -> str:
    text_lower = text.lower()
    industries = {
        "fintech":     ["fintech", "payment", "banking", "lending", "insurance", "neobank"],
        "healthtech":  ["healthtech", "medtech", "healthcare", "telemedicine", "medical"],
        "edtech":      ["edtech", "education", "learning", "school", "university", "course"],
        "saas":        ["saas", "software", "platform", "api", "b2b software", "cloud"],
        "ecommerce":   ["ecommerce", "marketplace", "retail", "shopping", "commerce"],
        "deeptech":    ["ai", "machine learning", "deep learning", "robotics", "biotech"],
    }
    for industry, keywords in industries.items():
        if any(kw in text_lower for kw in keywords):
            return industry
    return "saas"  # default


def _extract_section(text: str, triggers: list) -> str:
    text_lower = text.lower()
    for trigger in triggers:
        idx = text_lower.find(trigger)
        if idx != -1:
            snippet = text[idx:idx + 300].strip()
            # Get first 2 sentences
            sentences = snippet.split(".")
            return ". ".join(sentences[:2]).strip() if sentences else snippet[:200]
    return ""


def _extract_revenue(text: str) -> Optional[float]:
    patterns = [
        r"(?:revenue|arr|mrr)[^\d]*(?:inr|rs\.?|₹)?\s*([\d,]+)\s*(?:lakhs?|lacs?|cr|crore)?",
        r"(?:inr|rs\.?|₹)\s*([\d,]+)\s*(?:lakhs?|lacs?)",
        r"([\d,]+)\s*(?:lakhs?|lacs?)\s*(?:revenue|arr)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                return val
            except Exception:
                pass
    return None


def _extract_growth_rate(text: str) -> Optional[float]:
    patterns = [
        r"([\d]+)%\s*(?:growth|yoy|year.on.year|month.on.month|mom)",
        r"(?:growing|grew)\s*(?:at\s*)?([\d]+)%",
        r"([\d]+)x\s*growth",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if "x growth" in m.group(0).lower():
                    val = (val - 1) * 100
                return val
            except Exception:
                pass
    return None


def _extract_team_size(text: str) -> Optional[int]:
    patterns = [
        r"team\s*of\s*([\d]+)",
        r"([\d]+)\s*(?:full.time|employees|people|members)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None


def _extract_funding_stage(text: str) -> str:
    text_lower = text.lower()
    stages = ["series c", "series b", "series a", "pre-series a", "seed", "pre-seed", "bootstrapped"]
    for stage in stages:
        if stage in text_lower:
            return stage.title()
    return "Unknown"


def _extract_github_url(text: str) -> str:
    m = re.search(r"https?://github\.com/[\w\-]+/[\w\-]+", text)
    return m.group(0) if m else ""


def _estimate_confidence(text: str) -> str:
    if len(text) > 2000:
        return "HIGH"
    elif len(text) > 500:
        return "MEDIUM"
    return "LOW"


def _empty_extraction() -> dict:
    return {
        "company_name": "", "industry": "saas", "description": "",
        "problem": "", "solution": "", "revenue_inr_lakhs": None,
        "growth_rate_pct": None, "team_size": None,
        "funding_stage": "Unknown", "target_market": "",
        "github_url": "", "raw_text_preview": "",
        "extraction_confidence": "LOW",
    }
