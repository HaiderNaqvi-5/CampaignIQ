"""Backend verification boundary for Google identity credentials."""

from typing import Any
from app.core.config import settings


def verify_google_credential(credential: str) -> dict[str, Any]:
    """Verify signature, issuer, audience, expiry, and stable Google subject."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
    except ImportError as exc:
        raise RuntimeError("google-auth is required for Google authentication") from exc
    if not settings.GOOGLE_CLIENT_ID:
        raise ValueError("Google authentication is not configured")
    claims = id_token.verify_oauth2_token(credential, Request(), settings.GOOGLE_CLIENT_ID)
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise ValueError("Invalid Google issuer")
    if not claims.get("sub") or claims.get("email_verified") is not True:
        raise ValueError("Google identity is not verified")
    if not isinstance(claims.get("email"), str) or not claims["email"].strip():
        raise ValueError("Google identity has no verified email")
    return claims
