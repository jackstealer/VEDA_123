"""
VEDA — Natural Language API Sentiment Engine
Replaces LLM-based sentiment with Google Cloud Natural Language API.
"""
import logging
from typing import Optional
from utils.config import PROJECT_ID

logger = logging.getLogger(__name__)


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment using Google Cloud Natural Language API.
    Returns score (-1 to +1), magnitude, and label.
    """
    try:
        from google.cloud import language_v1
        client   = language_v1.LanguageServiceClient()
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT,
        )
        sentiment = client.analyze_sentiment(
            request={"document": document}
        ).document_sentiment

        score     = round(sentiment.score, 3)
        magnitude = round(sentiment.magnitude, 3)

        if score >= 0.25:
            label = "POSITIVE"
        elif score <= -0.25:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        logger.info(
            "[SentimentEngine] score=%.3f magnitude=%.3f label=%s",
            score, magnitude, label,
        )
        return {
            "score":     score,
            "magnitude": magnitude,
            "label":     label,
            "confidence": min(abs(score) + magnitude / 10, 1.0),
        }

    except Exception as exc:
        logger.warning("[SentimentEngine] NL API failed, using fallback: %s", exc)
        return _fallback_sentiment(text)


def _fallback_sentiment(text: str) -> dict:
    """Keyword-based fallback if NL API is unavailable."""
    text_lower = text.lower()
    positive_words = [
        "growth", "profit", "revenue", "success", "launch", "partnership",
        "funding", "expansion", "milestone", "award", "innovation", "strong",
        "positive", "excellent", "outstanding", "profitable",
    ]
    negative_words = [
        "loss", "decline", "lawsuit", "fraud", "bankruptcy", "scandal",
        "violation", "penalty", "breach", "crisis", "failed", "shutdown",
        "controversy", "investigation", "layoff", "downturn",
    ]
    pos = sum(1 for w in positive_words if w in text_lower)
    neg = sum(1 for w in negative_words if w in text_lower)
    total = max(pos + neg, 1)
    score = round((pos - neg) / total, 3)
    label = "POSITIVE" if score > 0.1 else "NEGATIVE" if score < -0.1 else "NEUTRAL"
    return {"score": score, "magnitude": round(abs(score), 3), "label": label, "confidence": 0.5}
