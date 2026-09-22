"""CampaignIQ authentication acceptance tests."""
from uuid import uuid4
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_password_registration_requires_otp_and_is_single_use(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth
    captured = {}
    monkeypatch.setattr(auth, "send_otp_email", lambda email, code: captured.update(email=email, code=code))
    email = f"otp-{uuid4()}@example.com"
    response = await client.post("/api/auth/register", json={"email": email, "password": "SecurePass123"})
    assert response.status_code == 202
    assert set(captured) == {"email", "code"}
    login = await client.post("/api/auth/login", json={"email": email, "password": "SecurePass123"})
    assert login.status_code == 403
    verified = await client.post("/api/auth/verify-otp", json={"email": email, "code": captured["code"]})
    assert verified.status_code == 200
    reused = await client.post("/api/auth/verify-otp", json={"email": email, "code": captured["code"]})
    assert reused.status_code == 400


@pytest.mark.asyncio
async def test_otp_resend_is_rate_limited(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth

    captured = []
    monkeypatch.setattr(auth, "send_otp_email", lambda email, code: captured.append(code))
    email = f"resend-{uuid4()}@example.com"

    assert (await client.post("/api/auth/register", json={"email": email, "password": "SecurePass123"})).status_code == 202
    resent = await client.post("/api/auth/resend-otp", json={"email": email})
    assert resent.status_code == 429
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_expired_otp_is_rejected(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth

    captured = {}
    monkeypatch.setattr(auth, "send_otp_email", lambda email, code: captured.update(code=code))
    monkeypatch.setattr(auth.settings, "OTP_EXPIRY_MINUTES", 0)
    email = f"expired-{uuid4()}@example.com"
    assert (await client.post("/api/auth/register", json={"email": email, "password": "SecurePass123"})).status_code == 202

    response = await client.post("/api/auth/verify-otp", json={"email": email, "code": captured["code"]})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_OTP"


@pytest.mark.asyncio
async def test_google_identity_creates_verified_user(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth
    monkeypatch.setattr(auth, "verify_google_credential", lambda _: {"sub": "google-test-sub", "email": f"google-{uuid4()}@example.com", "email_verified": True})
    response = await client.post("/api/auth/google", json={"credential": "test-credential"})
    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_google_identity_links_existing_verified_email(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth

    email = f"link-{uuid4()}@example.com"
    captured = {}
    monkeypatch.setattr(auth, "send_otp_email", lambda address, code: captured.update(code=code))
    assert (await client.post("/api/auth/register", json={"email": email, "password": "SecurePass123"})).status_code == 202
    assert (await client.post("/api/auth/verify-otp", json={"email": email, "code": captured["code"]})).status_code == 200
    monkeypatch.setattr(auth, "verify_google_credential", lambda _: {"sub": f"linked-google-{uuid4()}", "email": email, "email_verified": True})

    response = await client.post("/api/auth/google", json={"credential": "verified-credential"})
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_google_identity_requires_verified_email(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth

    monkeypatch.setattr(auth, "verify_google_credential", lambda _: {"sub": "unverified-sub", "email": "unverified@example.com", "email_verified": False})
    response = await client.post("/api/auth/google", json={"credential": "bad-credential"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_GOOGLE_CREDENTIAL"


@pytest.mark.asyncio
async def test_me_without_token_is_rejected(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
