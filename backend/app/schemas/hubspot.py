"""HubSpot API schemas. Provider-specific validation belongs in integrations."""
from pydantic import BaseModel


class HubSpotStatusResponse(BaseModel):
    connected: bool
    portal_id: str | None = None
