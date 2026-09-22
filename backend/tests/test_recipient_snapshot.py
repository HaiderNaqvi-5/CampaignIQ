from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.bot import Bot
from app.models.campaign import Campaign
from app.models.campaign_recipient import CampaignRecipient
from app.models.campaign_step import CampaignStep
from app.models.contact import Contact
from app.models.user import User
from app.schemas.campaign import RecipientSelection
from app.services.recipient_resolver import prepare_recipient_snapshot


@pytest.mark.asyncio
async def test_snapshot_deduplicates_and_excludes_invalid_contacts(db_session):
    user = User(email=f"snapshot-{uuid4()}@example.com", password_hash="hashed")
    db_session.add(user)
    await db_session.flush()
    bot = Bot(user_id=user.id, name="Snapshot site", website_url="https://snapshot.example", normalized_origin="https://snapshot.example")
    db_session.add(bot)
    await db_session.flush()
    campaign = Campaign(user_id=user.id, bot_id=bot.id, name="Test", topic="Topic", status="DRAFT")
    db_session.add(campaign)
    await db_session.flush()
    step = CampaignStep(campaign_id=campaign.id, step_order=1, delay_days=0, instructions="Topic", status="PENDING")
    db_session.add(step)
    contacts = [
        Contact(user_id=user.id, hubspot_id="1", email="person@example.com"),
        Contact(user_id=user.id, hubspot_id="2", email="PERSON@example.com"),
        Contact(user_id=user.id, hubspot_id="3", email=None),
    ]
    db_session.add_all(contacts)
    await db_session.flush()

    result = await prepare_recipient_snapshot(
        campaign,
        RecipientSelection(contact_ids=[contact.id for contact in contacts]),
        user.id,
        db_session,
    )

    assert result["prepared"] == 1
    assert len(result["duplicate_contact_ids"]) == 1
    assert len(result["ineligible_contact_ids"]) == 1
    recipients = (await db_session.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))).scalars().all()
    assert len(recipients) == 1
    assert recipients[0].contact_id == contacts[0].id


@pytest.mark.asyncio
async def test_snapshot_does_not_include_another_users_contact(db_session):
    owner = User(email=f"owner-{uuid4()}@example.com", password_hash="hashed")
    other = User(email=f"other-{uuid4()}@example.com", password_hash="hashed")
    db_session.add_all([owner, other])
    await db_session.flush()
    bot = Bot(user_id=owner.id, name="Owner site", website_url="https://owner.example", normalized_origin="https://owner.example")
    db_session.add(bot)
    await db_session.flush()
    campaign = Campaign(user_id=owner.id, bot_id=bot.id, name="Test", topic="Topic", status="DRAFT")
    db_session.add(campaign)
    await db_session.flush()
    db_session.add(CampaignStep(campaign_id=campaign.id, step_order=1, delay_days=0, instructions="Topic", status="PENDING"))
    foreign = Contact(user_id=other.id, hubspot_id="foreign", email="foreign@example.com")
    db_session.add(foreign)
    await db_session.flush()

    result = await prepare_recipient_snapshot(campaign, RecipientSelection(contact_ids=[foreign.id]), owner.id, db_session)

    assert result["prepared"] == 0
    assert result["ineligible_contact_ids"] == []
    assert result["duplicate_contact_ids"] == []
