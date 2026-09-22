"""Campaign creation and immutable recipient snapshot routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.bot import Bot
from app.models.campaign import Campaign
from app.models.campaign_step import CampaignStep
from app.models.campaign_recipient import CampaignRecipient
from app.models.user import User
from app.schemas.campaign import CampaignCreateRequest, CampaignEmailUpdateRequest, CampaignListItem, CampaignResponse, RecipientSelection, RecipientSnapshotResponse
from app.services.campaign_service import generate_campaign_emails
from app.services.recipient_resolver import prepare_recipient_snapshot

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(req: CampaignCreateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    bot = (await db.execute(select(Bot).where(Bot.id == req.bot_id, Bot.user_id == current_user.id))).scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail={"code": "WEBSITE_NOT_FOUND", "message": "Website not found or access denied"})
    campaign = Campaign(user_id=current_user.id, bot_id=bot.id, name=req.name.strip(), topic=req.topic.strip(), offer=req.offer.strip() if req.offer else None, status="DRAFT")
    db.add(campaign)
    await db.flush()
    db.add(CampaignStep(campaign_id=campaign.id, step_order=1, delay_days=0, instructions=req.offer or req.topic, status="PENDING"))
    for index, follow_up in enumerate(req.follow_ups, start=2):
        db.add(CampaignStep(campaign_id=campaign.id, step_order=index, delay_days=follow_up.delay_days, instructions=follow_up.instructions, status="PENDING"))
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignListItem])
async def list_campaigns(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Campaign, func.count(CampaignRecipient.id))
        .outerjoin(CampaignRecipient, CampaignRecipient.campaign_id == Campaign.id)
        .where(Campaign.user_id == current_user.id)
        .group_by(Campaign.id)
        .order_by(Campaign.created_at.desc())
    )
    return [CampaignListItem.model_validate(campaign).model_copy(update={"recipient_count": count}) for campaign, count in rows]


@router.post("/{campaign_id}/recipients", response_model=RecipientSnapshotResponse)
async def prepare_recipients(campaign_id: UUID, req: RecipientSelection, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found or access denied"})
    if (await db.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))).scalars().first():
        raise HTTPException(status_code=409, detail={"code": "RECIPIENTS_ALREADY_PREPARED", "message": "Recipients are already snapshotted"})
    try:
        return await prepare_recipient_snapshot(campaign, req, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_RECIPIENT_SELECTION", "message": str(exc)}) from exc


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found or access denied"})
    recipients = (await db.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))).scalars().all()
    return {"campaign": campaign, "recipients": recipients}


@router.post("/{campaign_id}/generate")
async def generate_campaign(campaign_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found or access denied"})
    if not (await db.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))).scalars().first():
        raise HTTPException(status_code=409, detail={"code": "RECIPIENTS_NOT_PREPARED", "message": "Prepare recipients before generating emails"})
    return await generate_campaign_emails(campaign, db)


@router.patch("/{campaign_id}/emails/{recipient_id}")
async def update_campaign_email(campaign_id: UUID, recipient_id: UUID, req: CampaignEmailUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))).scalar_one_or_none()
    recipient = (await db.execute(select(CampaignRecipient).where(CampaignRecipient.id == recipient_id, CampaignRecipient.campaign_id == campaign_id))).scalar_one_or_none()
    if not campaign or not recipient:
        raise HTTPException(status_code=404, detail={"code": "RECIPIENT_NOT_FOUND", "message": "Campaign recipient not found or access denied"})
    if campaign.status not in {"DRAFT", "GENERATING", "READY"}:
        raise HTTPException(status_code=409, detail={"code": "CAMPAIGN_NOT_EDITABLE", "message": "Campaign emails cannot be edited after delivery starts"})
    recipient.subject, recipient.body = req.subject.strip(), req.body.strip()
    recipient.status, recipient.error = "GENERATED", None
    first_step = (await db.execute(select(CampaignStep).where(CampaignStep.campaign_id == campaign.id, CampaignStep.step_order == 1))).scalar_one()
    first_step_statuses = (await db.execute(select(CampaignRecipient.status).where(CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.step_id == first_step.id))).scalars().all()
    if first_step_statuses and all(item == "GENERATED" for item in first_step_statuses):
        campaign.status = "READY"
    await db.commit()
    return {"recipient_id": recipient.id, "subject": recipient.subject, "body": recipient.body, "status": recipient.status, "campaign_status": campaign.status}


@router.post("/{campaign_id}/send")
async def send_campaign(campaign_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found or access denied"})
    if campaign.status != "READY":
        raise HTTPException(status_code=409, detail={"code": "CAMPAIGN_NOT_READY", "message": "Campaign must be ready for review before sending"})
    first_step = (await db.execute(select(CampaignStep).where(CampaignStep.campaign_id == campaign.id, CampaignStep.step_order == 1))).scalar_one()
    recipients = (await db.execute(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.step_id == first_step.id))).scalars().all()
    if not recipients or any(recipient.status != "GENERATED" for recipient in recipients):
        raise HTTPException(status_code=409, detail={"code": "CAMPAIGN_EMAILS_INCOMPLETE", "message": "All eligible recipient emails must be generated or reviewed before sending"})
    campaign.status = "SENDING"
    await db.commit()
    from app.jobs.tasks import enqueue_campaign_send
    queued = enqueue_campaign_send(campaign.id)
    return {"campaign_id": campaign.id, "status": campaign.status, "queued": queued}
