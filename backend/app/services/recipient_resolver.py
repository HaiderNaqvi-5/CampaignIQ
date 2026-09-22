"""Tenant-scoped recipient resolution and immutable campaign snapshots."""
import re
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.hubspot.service import get_client
from app.models.campaign import Campaign
from app.models.campaign_recipient import CampaignRecipient
from app.models.campaign_step import CampaignStep
from app.models.contact import Contact
from app.models.hubspot_connection import HubSpotConnection
from app.models.hubspot_list import HubSpotList

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def resolve_contacts(campaign: Campaign, selection, user_id: UUID, db: AsyncSession):
    """Resolve one selection mode and return unique contacts plus reporting IDs."""
    if selection.contact_ids:
        contacts = (await db.execute(select(Contact).where(Contact.user_id == user_id, Contact.id.in_(selection.contact_ids)))).scalars().all()
    elif selection.all:
        contacts = (await db.execute(select(Contact).where(Contact.user_id == user_id))).scalars().all()
    else:
        lists = (await db.execute(select(HubSpotList).where(HubSpotList.user_id == user_id, HubSpotList.id.in_(selection.list_ids)))).scalars().all()
        if len(lists) != len(set(selection.list_ids)):
            raise ValueError("One or more HubSpot lists were not found")
        connection = (await db.execute(select(HubSpotConnection).where(HubSpotConnection.user_id == user_id))).scalar_one_or_none()
        if not connection:
            raise ValueError("Connect HubSpot before selecting a list")
        client = await get_client(connection, db)
        hubspot_ids = set()
        for hubspot_list in lists:
            after = None
            while True:
                payload = await client.list_memberships(hubspot_list.hubspot_id, after)
                hubspot_ids.update(str(item.get("recordId", item.get("id"))) for item in payload.get("results", []))
                after = (payload.get("paging") or {}).get("next", {}).get("after")
                if not after: break
        contacts = (await db.execute(select(Contact).where(Contact.user_id == user_id, Contact.hubspot_id.in_(hubspot_ids)))).scalars().all()

    unique = []
    seen_emails = set()
    duplicate_ids = []
    ineligible_ids = []
    for contact in contacts:
        email = (contact.email or "").strip().lower()
        if not _EMAIL_RE.match(email):
            ineligible_ids.append(contact.id)
            continue
        if email in seen_emails:
            duplicate_ids.append(contact.id)
            continue
        seen_emails.add(email)
        unique.append(contact)
    return unique, ineligible_ids, duplicate_ids


async def prepare_recipient_snapshot(campaign: Campaign, selection, user_id: UUID, db: AsyncSession):
    contacts, ineligible_ids, duplicate_ids = await resolve_contacts(campaign, selection, user_id, db)
    steps = (await db.execute(select(CampaignStep).where(CampaignStep.campaign_id == campaign.id).order_by(CampaignStep.step_order))).scalars().all()
    if not steps:
        raise ValueError("Campaign has no delivery steps")
    existing = (await db.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))).scalars().all()
    if existing:
        return {"prepared": len(existing), "ineligible_contact_ids": ineligible_ids, "duplicate_contact_ids": duplicate_ids}
    for contact in contacts:
        for step in steps:
            db.add(CampaignRecipient(campaign_id=campaign.id, contact_id=contact.id, step_id=step.id, status="PENDING"))
    await db.commit()
    return {"prepared": len(contacts), "ineligible_contact_ids": ineligible_ids, "duplicate_contact_ids": duplicate_ids}
