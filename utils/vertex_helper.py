"""
VEDA — Vertex AI wrapper.
Single entry point for all Gemini calls with structured logging and retry.
"""
import time
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from utils.config import PROJECT_ID, LOCATION, VERTEX_AI_MODEL

logger = logging.getLogger(__name__)

_model: GenerativeModel | None = None


def _get_model() -> GenerativeModel:
    global _model
    if _model is None:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        _model = GenerativeModel(VERTEX_AI_MODEL)
        logger.info("Vertex AI initialised — model: %s", VERTEX_AI_MODEL)
    return _model


def ask_gemini(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 8192,
    context: str = "",
) -> str:
    """
    Send a prompt to Gemini. Retries up to 3 times on rate limit.

    Args:
        prompt:      The full prompt string.
        temperature: Lower = more deterministic. Keep at 0.2 for scoring.
        max_tokens:  Max output tokens.
        context:     Optional label for logging (e.g. "CodeAuditor").

    Returns:
        Raw text response from Gemini.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    model  = _get_model()
    config = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    label = f"[Gemini:{context}]" if context else "[Gemini]"

    for attempt in range(1, 4):
        try:
            logger.debug("%s Sending prompt (attempt %d, ~%d chars)",
                         label, attempt, len(prompt))
            t0       = time.monotonic()
            response = model.generate_content(prompt, generation_config=config)
            elapsed  = round(time.monotonic() - t0, 2)

            text = _extract_text(response)
            logger.info("%s Response received in %.2fs (%d chars)",
                        label, elapsed, len(text))
            return text

        except Exception as exc:
            is_rate_limit = any(
                marker in str(exc)
                for marker in ("429", "Resource exhausted", "RESOURCE_EXHAUSTED")
            )
            if is_rate_limit and attempt < 3:
                wait = 30 * attempt
                logger.warning("%s Rate limited — waiting %ds (attempt %d/3)",
                               label, wait, attempt)
                time.sleep(wait)
                continue

            logger.error("%s Failed on attempt %d: %s", label, attempt, exc)
            raise RuntimeError(f"Gemini call failed: {exc}") from exc

    raise RuntimeError("Gemini rate limit exceeded after 3 retries")


def _extract_text(response) -> str:
    """Extract text from Gemini response, handling partial/blocked responses."""
    try:
        return response.text
    except ValueError:
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    return part.text
        return ""
