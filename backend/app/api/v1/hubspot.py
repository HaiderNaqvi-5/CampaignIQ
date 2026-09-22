"""HubSpot CRM OAuth and synchronization routes."""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.db.session import get_db
from app.integrations.hubspot.oauth import access_token_metadata, build_authorization_url, consume_state, create_state, exchange_code
from app.integrations.hubspot.service import get_client, sync_contacts, sync_lists
from app.models.hubspot_connection import HubSpotConnection
from app.models.hubspot_list import HubSpotList
from app.models.user import User
from app.schemas.hubspot import HubSpotStatusResponse

router = APIRouter(prefix="/hubspot", tags=["HubSpot"])


@router.get("/connect")
async def connect(current_user: User = Depends(get_current_user)):
    if not settings.HUBSPOT_CLIENT_ID or not settings.HUBSPOT_CLIENT_SECRET or not settings.TOKEN_ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail={"code": "HUBSPOT_NOT_CONFIGURED", "message": "HubSpot integration is not configured"})
    return {"authorization_url": build_authorization_url(create_state(str(current_user.id)))}


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, error: str | None = None, db: AsyncSession = Depends(get_db)):
    if error or not code or not state:
        raise HTTPException(status_code=400, detail={"code": "HUBSPOT_OAUTH_FAILED", "message": "HubSpot authorization was not completed"})
    try:
        claims = await consume_state(state)
        tokens = await exchange_code(code)
        metadata = await access_token_metadata(tokens["access_token"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"code": "HUBSPOT_OAUTH_FAILED", "message": "HubSpot authorization could not be completed"}) from exc
    user_id = UUID(claims["sub"])
    connection = (await db.execute(select(HubSpotConnection).where(HubSpotConnection.user_id == user_id))).scalar_one_or_none()
    values = dict(user_id=user_id, portal_id=str(metadata.get("hub_id")), access_token_encrypted=encrypt_secret(tokens["access_token"]), refresh_token_encrypted=encrypt_secret(tokens["refresh_token"]), expires_at=datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 1800))))
    if connection:
        for key, value in values.items(): setattr(connection, key, value)
    else:
        db.add(HubSpotConnection(**values))
    await db.commit()
    return RedirectResponse(settings.FRONTEND_ORIGIN + "/dashboard/hubspot?connected=1")


@router.get("/status", response_model=HubSpotStatusResponse)
async def status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    connection = (await db.execute(select(HubSpotConnection).where(HubSpotConnection.user_id == current_user.id))).scalar_one_or_none()
    return HubSpotStatusResponse(connected=connection is not None, portal_id=connection.portal_id if connection else None)


@router.post("/sync")
async def sync(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    connection = (await db.execute(select(HubSpotConnection).where(HubSpotConnection.user_id == current_user.id))).scalar_one_or_none()
    if not connection: raise HTTPException(status_code=400, detail={"code": "HUBSPOT_NOT_CONNECTED", "message": "Connect HubSpot first"})
    return {"contacts_synced": await sync_contacts(connection, current_user.id, db), "lists_synced": await sync_lists(connection, current_user.id, db)}


@router.get("/lists")
async def lists(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    records = (await db.execute(select(HubSpotList).where(HubSpotList.user_id == current_user.id).order_by(HubSpotList.name))).scalars().all()
    return records
