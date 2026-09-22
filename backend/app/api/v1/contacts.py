"""Tenant-scoped synced HubSpot contacts."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.integrations.hubspot.service import get_client
from app.models.contact import Contact
from app.models.hubspot_connection import HubSpotConnection
from app.models.user import User
from app.schemas.contact import ContactResponse, ContactUpdateRequest

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("", response_model=list[ContactResponse])
async def get_contacts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Contact).where(Contact.user_id == current_user.id).order_by(Contact.email))).scalars().all()


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(contact_id: UUID, req: ContactUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    contact = (await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id))).scalar_one_or_none()
    if not contact: raise HTTPException(status_code=404, detail={"code": "CONTACT_NOT_FOUND", "message": "Contact not found"})
    connection = (await db.execute(select(HubSpotConnection).where(HubSpotConnection.user_id == current_user.id))).scalar_one_or_none()
    if not connection: raise HTTPException(status_code=400, detail={"code": "HUBSPOT_NOT_CONNECTED", "message": "Connect HubSpot first"})
    fields = req.model_dump(exclude_unset=True)
    hubspot_fields = {"firstname": fields.get("first_name"), "lastname": fields.get("last_name"), "email": fields.get("email"), "company": fields.get("company"), "jobtitle": fields.get("job_title")}
    await (await get_client(connection, db)).update_contact(contact.hubspot_id, {key: value for key, value in hubspot_fields.items() if value is not None})
    for key, value in fields.items(): setattr(contact, key, str(value) if value is not None else None)
    contact.raw_properties = {**contact.raw_properties, **{key: value for key, value in hubspot_fields.items() if value is not None}}
    await db.commit()
    await db.refresh(contact)
    return contact
