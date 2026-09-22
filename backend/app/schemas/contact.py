"""Contact and list schemas for the local HubSpot cache."""
from uuid import UUID
from pydantic import BaseModel, EmailStr


class ContactResponse(BaseModel):
    id: UUID
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    job_title: str | None = None

    class Config:
        from_attributes = True


class ContactUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    company: str | None = None
    job_title: str | None = None
