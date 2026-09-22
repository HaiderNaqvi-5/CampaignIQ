"""Campaign orchestration: grounded per-recipient generation and statuses."""

import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot
from app.models.brand import BrandSettings
from app.models.campaign import Campaign
from app.models.campaign_recipient import CampaignRecipient
from app.models.campaign_step import CampaignStep
from app.models.contact import Contact
from app.services.campaign_prompt import build_campaign_system_prompt, build_campaign_user_prompt, parse_generated_email
from app.services.embedding_service import get_embedding_provider
from app.services.llm_service import get_llm_provider
from app.services.retrieval import retrieve_chunks


async def generate_recipient_email(recipient: CampaignRecipient, campaign: Campaign, step: CampaignStep, db: AsyncSession) -> tuple[str, str]:
    contact = (await db.execute(select(Contact).where(Contact.id == recipient.contact_id))).scalar_one()
    bot = (await db.execute(select(Bot).where(Bot.id == campaign.bot_id, Bot.user_id == campaign.user_id))).scalar_one()
    brand = (await db.execute(select(BrandSettings).where(BrandSettings.bot_id == bot.id))).scalar_one_or_none()
    query = f"{campaign.topic} {step.instructions} {contact.company or ''} {contact.job_title or ''}".strip()
    embedding = await get_embedding_provider().embed_query(query)
    chunks = await retrieve_chunks(bot.id, embedding, db, top_k=6, min_similarity=0.0)
    context = "\n".join(f'<chunk source="{c.source_url}">{c.content}</chunk>' for c in chunks)
    company_name = (brand.company_name if brand else None) or bot.name
    system = build_campaign_system_prompt(company_name, (brand.writing_style if brand else {}) or {}, context)
    previous_email = None
    if step.step_order > 1:
        previous_step = (await db.execute(
            select(CampaignStep).where(
                CampaignStep.campaign_id == campaign.id,
                CampaignStep.step_order == step.step_order - 1,
            )
        )).scalar_one_or_none()
        if previous_step:
            previous_recipient = (await db.execute(
                select(CampaignRecipient).where(
                    CampaignRecipient.campaign_id == campaign.id,
                    CampaignRecipient.contact_id == recipient.contact_id,
                    CampaignRecipient.step_id == previous_step.id,
                )
            )).scalar_one_or_none()
            if previous_recipient:
                previous_email = {"subject": previous_recipient.subject, "body": previous_recipient.body}
    raw = await get_llm_provider().complete_chat(
        [{"role": "user", "content": build_campaign_user_prompt(campaign, step, contact, previous_email)}],
        system,
    )
    return parse_generated_email(raw)


async def generate_campaign_emails(campaign: Campaign, db: AsyncSession) -> dict:
    recipients = (await db.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))).scalars().all()
    step = (await db.execute(select(CampaignStep).where(CampaignStep.campaign_id == campaign.id, CampaignStep.step_order == 1))).scalar_one()
    campaign.status = "GENERATING"
    await db.commit()
    generated = failed = 0
    for recipient in recipients:
        try:
            recipient.subject, recipient.body = await generate_recipient_email(recipient, campaign, step, db)
            recipient.status = "GENERATED"
            generated += 1
        except Exception as exc:
            recipient.status = "FAILED"
            recipient.error = str(exc)[:2000]
            failed += 1
        await db.commit()
    # Generation errors are recipient-scoped and remain recoverable through
    # review/edit or a retry. Keep the campaign in a draftable state until
    # every eligible step-one recipient is generated; PARTIAL_FAILED and
    # FAILED are reserved for terminal delivery outcomes.
    campaign.status = "READY" if generated and not failed else "DRAFT"
    await db.commit()
    return {"generated": generated, "failed": failed}
