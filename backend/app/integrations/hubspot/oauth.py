"""HubSpot OAuth authorization, state validation, and token exchange."""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
import redis.asyncio as aioredis
from jose import JWTError, jwt
from app.core.config import settings

_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"


def build_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.HUBSPOT_CLIENT_ID,
        "redirect_uri": settings.HUBSPOT_REDIRECT_URI,
        "scope": settings.HUBSPOT_SCOPES,
        "state": state,
    }
    return "https://app.hubspot.com/oauth/authorize?" + urlencode(params)


def create_state(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "jti": secrets.token_urlsafe(24), "purpose": "hubspot_oauth", "iat": now, "exp": now + timedelta(minutes=10)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired HubSpot OAuth state") from exc
    if payload.get("purpose") != "hubspot_oauth" or not payload.get("sub") or not payload.get("jti"):
        raise ValueError("Invalid HubSpot OAuth state")
    return payload


async def exchange_code(code: str) -> dict:
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": settings.HUBSPOT_REDIRECT_URI, "client_id": settings.HUBSPOT_CLIENT_ID, "client_secret": settings.HUBSPOT_CLIENT_SECRET}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": settings.HUBSPOT_CLIENT_ID, "client_secret": settings.HUBSPOT_CLIENT_SECRET}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


async def access_token_metadata(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"https://api.hubapi.com/oauth/v1/access-tokens/{access_token}")
        response.raise_for_status()
        return response.json()


async def consume_state(state: str) -> dict:
    """Validate and atomically consume an OAuth state token.

    The JWT provides integrity and expiry; Redis provides one-time-use
    protection when the callback is retried or replayed.
    """
    payload = decode_state(state)
    now = datetime.now(timezone.utc)
    expires_at = payload.get("exp")
    ttl = max(1, int(float(expires_at) - now.timestamp())) if expires_at else 600
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        key = f"campaigniq:hubspot:oauth-state:{payload['jti']}"
        accepted = await client.set(key, "1", ex=ttl, nx=True)
        if not accepted:
            raise ValueError("HubSpot OAuth state has already been used")
    finally:
        await client.aclose()
    return payload
