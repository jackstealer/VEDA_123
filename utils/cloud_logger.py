"""
VEDA — Cloud Logging
Structured logging to Google Cloud Logging for all agents and API calls.
Judges can see real-time logs in GCP Console → Logging → Log Explorer.
"""
import logging
import os

_cloud_logging_enabled = False

def setup_cloud_logging():
    """
    Initialise Google Cloud Logging.
    Falls back to standard logging if unavailable.
    """
    global _cloud_logging_enabled
    try:
        import google.cloud.logging
        from google.cloud.logging.handlers import CloudLoggingHandler

        project = os.getenv("GOOGLE_CLOUD_PROJECT", "veda-491808")
        client  = google.cloud.logging.Client(project=project)

        # Attach Cloud Logging handler to root logger
        handler = CloudLoggingHandler(client, name="veda-agent-logs")
        handler.setLevel(logging.INFO)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

        # Also keep stdout for Cloud Run
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s — %(message)s")
        stream_handler.setFormatter(fmt)
        root_logger.addHandler(stream_handler)

        _cloud_logging_enabled = True
        logging.getLogger(__name__).info(
            "Cloud Logging initialised — project: %s", project
        )

    except Exception as exc:
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        )
        logging.getLogger(__name__).warning(
            "Cloud Logging unavailable — using stdout: %s", exc
        )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Call setup_cloud_logging() once at startup."""
    return logging.getLogger(name)


def log_audit_event(
    job_id: str,
    agent: str,
    event: str,
    score: float = None,
    metadata: dict = None,
):
    """
    Log a structured audit event visible in Cloud Logging.
    Appears in GCP Console with full JSON payload.
    """
    logger = logging.getLogger("veda.audit")
    extra  = {
        "json_fields": {
            "job_id":   job_id,
            "agent":    agent,
            "event":    event,
            "score":    score,
            **(metadata or {}),
        }
    }
    logger.info(
        "[%s] %s — %s%s",
        agent, event,
        f"score={score} " if score is not None else "",
        f"job={job_id[:8]}",
        extra=extra,
    )
