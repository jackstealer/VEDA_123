"""
VEDA — Central configuration.
Reads secrets from Google Cloud Secret Manager in production.
Falls back to environment variables for local development.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_secret(secret_id: str, fallback_env: str) -> str:
    """
    Fetch secret from Google Cloud Secret Manager.
    Falls back to environment variable if Secret Manager is unavailable.
    """
    try:
        from google.cloud import secretmanager
        client  = secretmanager.SecretManagerServiceClient()
        name    = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
        payload = client.access_secret_version(request={"name": name})
        value   = payload.payload.data.decode("utf-8").strip()
        logger.debug("Loaded secret from Secret Manager: %s", secret_id)
        return value
    except Exception:
        value = os.getenv(fallback_env, "")
        if value:
            logger.debug("Loaded from env fallback: %s", fallback_env)
        return value


# ── Google Cloud ──────────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "veda-491808")
LOCATION   = os.getenv("GCP_LOCATION",   "us-central1")

# ── BigQuery ──────────────────────────────────────────────────────────────────
BQ_DATASET = os.getenv("BQ_DATASET", "veda_ma_diligence")

# ── Vertex AI ─────────────────────────────────────────────────────────────────
VERTEX_AI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")

# ── MCP Server ────────────────────────────────────────────────────────────────
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

# ── Agent timeouts (seconds) ──────────────────────────────────────────────────
AGENT_TIMEOUT_CODE       = int(os.getenv("AGENT_TIMEOUT_CODE",       "120"))
AGENT_TIMEOUT_REGULATORY = int(os.getenv("AGENT_TIMEOUT_REGULATORY", "90"))
AGENT_TIMEOUT_MARKET = int(os.getenv("AGENT_TIMEOUT_MARKET", "180"))
AGENT_TIMEOUT_SUMMARY    = int(os.getenv("AGENT_TIMEOUT_SUMMARY",    "60"))

# ── Secrets (Secret Manager → env fallback) ───────────────────────────────────
GITHUB_TOKEN         = _get_secret("GITHUB-TOKEN",        "GITHUB_TOKEN")
GOOGLE_CLIENT_ID     = _get_secret("GOOGLE-CLIENT-ID",    "GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _get_secret("GOOGLE-CLIENT-SECRET","GOOGLE_CLIENT_SECRET")
SESSION_SECRET       = _get_secret("SESSION-SECRET",       "SESSION_SECRET")

# ── OAuth ─────────────────────────────────────────────────────────────────────
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "")

# ── Validation ────────────────────────────────────────────────────────────────
if not GITHUB_TOKEN:
    logger.warning("GITHUB_TOKEN not set — GitHub API rate limited to 60 req/hr")
if not GOOGLE_CLIENT_ID:
    logger.warning("GOOGLE_CLIENT_ID not set — OAuth login will not work")
if not PROJECT_ID:
    raise EnvironmentError("GCP_PROJECT_ID is required")
