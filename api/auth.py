"""
VEDA — Google OAuth 2.0 authentication.
Handles login, callback, session management, and per-user token storage.
"""
import logging
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.config import Config

from utils.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    OAUTH_REDIRECT_URI,
    SESSION_SECRET,
)

logger = logging.getLogger(__name__)

_config = Config(environ={
    "GOOGLE_CLIENT_ID":     GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
})

oauth = OAuth(_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/calendar "
            "https://www.googleapis.com/auth/tasks"
        ),
        "prompt": "consent select_account",
    },
)

_serialiser    = URLSafeTimedSerializer(SESSION_SECRET)
SESSION_COOKIE = "veda_session"
_SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours


def create_session_token(user: dict) -> str:
    return _serialiser.dumps(user)


def decode_session_token(token: str) -> Optional[dict]:
    try:
        return _serialiser.loads(token, max_age=_SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return decode_session_token(token)


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login at /login",
        )
    return user


def get_user_access_token(request: Request) -> Optional[str]:
    """Extract the Google OAuth access token for the current user."""
    user = get_current_user(request)
    if not user:
        return None
    return user.get("access_token")
