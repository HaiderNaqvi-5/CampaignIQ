from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.hubspot_connection import HubSpotConnection
from app.models.hubspot_list import HubSpotList
from app.models.user import User
@pytest.mark.asyncio
async def test_sync_lists_consumes_all_pages(db_session, monkeypatch):
    from app.integrations.hubspot import service

    user = User(email=f"lists-{uuid4()}@example.com", password_hash="hashed")
    db_session.add(user)
    await db_session.flush()
    connection = HubSpotConnection(
        user_id=user.id,
        portal_id="portal-1",
        access_token_encrypted="access",
        refresh_token_encrypted="refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(connection)
    await db_session.flush()

    class FakeClient:
        def __init__(self):
            self.afters = []

        async def list_segments(self, after=None):
            self.afters.append(after)
            if after is None:
                return {"results": [{"id": "list-1", "name": "First"}], "paging": {"next": {"after": "next-page"}}}
            return {"results": [{"id": "list-2", "name": "Second"}]}

    fake = FakeClient()
    monkeypatch.setattr(service, "get_client", lambda *_args, **_kwargs: _async_value(fake))

    assert await service.sync_lists(connection, user.id, db_session) == 2
    assert fake.afters == [None, "next-page"]
    records = (await db_session.execute(select(HubSpotList).where(HubSpotList.user_id == user.id))).scalars().all()
    assert {record.hubspot_id for record in records} == {"list-1", "list-2"}


async def _async_value(value):
    return value
