"""HubSpot synchronization and supported contact edits."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crypto import decrypt_secret, encrypt_secret
from app.integrations.hubspot.client import HubSpotClient
from app.integrations.hubspot.oauth import refresh_access_token
from app.models.contact import Contact
from app.models.hubspot_connection import HubSpotConnection
from app.models.hubspot_list import HubSpotList


async def get_client(connection: HubSpotConnection, db: AsyncSession) -> HubSpotClient:
    if connection.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=30):
        tokens = await refresh_access_token(decrypt_secret(connection.refresh_token_encrypted))
        connection.access_token_encrypted = encrypt_secret(tokens["access_token"])
        connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 1800)))
        await db.commit()
    return HubSpotClient(decrypt_secret(connection.access_token_encrypted))


async def sync_contacts(connection: HubSpotConnection, user_id, db: AsyncSession) -> int:
    client = await get_client(connection, db)
    count = 0
    after = None
    while True:
        payload = await client.list_contacts(after)
        for item in payload.get("results", []):
            props = item.get("properties", {})
            record = (await db.execute(select(Contact).where(Contact.user_id == user_id, Contact.hubspot_id == item["id"]))).scalar_one_or_none()
            values = dict(user_id=user_id, hubspot_id=item["id"], email=props.get("email"), first_name=props.get("firstname"), last_name=props.get("lastname"), company=props.get("company"), job_title=props.get("jobtitle"), raw_properties=props, last_synced_at=datetime.now(timezone.utc))
            if record:
                for key, value in values.items(): setattr(record, key, value)
            else:
                db.add(Contact(**values))
            count += 1
        after = (payload.get("paging") or {}).get("next", {}).get("after")
        if not after: break
    await db.commit()
    return count


async def sync_lists(connection: HubSpotConnection, user_id, db: AsyncSession) -> int:
    client = await get_client(connection, db)
    count = 0
    after = None
    while True:
        payload = await client.list_segments(after)
        for item in payload.get("lists", payload.get("results", [])):
            hubspot_id = str(item.get("listId", item.get("id")))
            record = (await db.execute(select(HubSpotList).where(HubSpotList.user_id == user_id, HubSpotList.hubspot_id == hubspot_id))).scalar_one_or_none()
            values = dict(user_id=user_id, hubspot_id=hubspot_id, name=item.get("name", "Unnamed list"), last_synced_at=datetime.now(timezone.utc))
            if record:
                for key, value in values.items(): setattr(record, key, value)
            else: db.add(HubSpotList(**values))
            count += 1
        after = (payload.get("paging") or {}).get("next", {}).get("after")
        if not after:
            break
    await db.commit()
    return count
