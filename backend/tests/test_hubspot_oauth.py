from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from app.integrations.hubspot import oauth


def test_authorization_url_contains_signed_state_parameters(monkeypatch):
    monkeypatch.setattr(settings, "HUBSPOT_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "HUBSPOT_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setattr(settings, "HUBSPOT_SCOPES", "contacts.read")

    state = oauth.create_state("user-123")
    query = parse_qs(urlparse(oauth.build_authorization_url(state)).query)

    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["http://localhost/callback"]
    assert query["state"] == [state]
    assert oauth.decode_state(state)["sub"] == "user-123"


@pytest.mark.asyncio
async def test_oauth_state_is_consumed_once(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.keys = set()

        async def set(self, key, value, ex, nx):
            if key in self.keys:
                return None
            self.keys.add(key)
            return True

        async def aclose(self):
            return None

    fake = FakeRedis()
    monkeypatch.setattr(oauth.aioredis, "from_url", lambda *args, **kwargs: fake)
    state = oauth.create_state("user-123")

    assert (await oauth.consume_state(state))["sub"] == "user-123"
    with pytest.raises(ValueError, match="already been used"):
        await oauth.consume_state(state)
