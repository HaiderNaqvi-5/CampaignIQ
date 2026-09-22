"""Campaign request/response contracts; business rules live in services."""
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class RecipientSelection(BaseModel):
    contact_ids: list[UUID] = Field(default_factory=list)
    list_ids: list[UUID] = Field(default_factory=list)
    all: bool = False

    @model_validator(mode="after")
    def exactly_one_mode(self):
        if sum(bool(value) for value in (self.contact_ids, self.list_ids, self.all)) != 1:
            raise ValueError("Choose exactly one recipient selection mode")
        return self


class CampaignCreateRequest(BaseModel):
    bot_id: UUID
    name: str = Field(min_length=1, max_length=255)
    topic: str = Field(min_length=1)
    offer: str | None = None
    # Recipient resolution is deliberately a second request.  This keeps the
    # campaign editable while the user reviews the selection and makes the
    # snapshot boundary explicit.
    recipients: RecipientSelection | None = None
    follow_ups: list["CampaignStepInput"] = Field(default_factory=list)


class CampaignResponse(BaseModel):
    id: UUID
    user_id: UUID
    bot_id: UUID
    name: str
    topic: str
    offer: str | None
    status: str

    model_config = {"from_attributes": True}


class CampaignListItem(CampaignResponse):
    recipient_count: int = 0


class CampaignStepInput(BaseModel):
    delay_days: int = Field(ge=1, le=365)
    instructions: str = Field(min_length=1, max_length=10000)


class RecipientSnapshotResponse(BaseModel):
    prepared: int
    ineligible_contact_ids: list[UUID] = Field(default_factory=list)
    duplicate_contact_ids: list[UUID] = Field(default_factory=list)


class CampaignEmailUpdateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50000)
