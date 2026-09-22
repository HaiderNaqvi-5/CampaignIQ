"""Authenticated HubSpot CRM client using current date-versioned APIs."""
from typing import Any
import httpx
from app.core.config import settings


class HubSpotClient:
    """Small adapter for only the CRM operations CampaignIQ requires."""

    def __init__(self, access_token: str):
        self.access_token = access_token

    @property
    def base_url(self) -> str:
        return "https://api.hubapi.com"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, self.base_url + path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}

    async def list_contacts(self, after: str | None = None) -> dict:
        params = {"limit": 100, "properties": "email,firstname,lastname,company,jobtitle,hs_object_id"}
        if after:
            params["after"] = after
        return await self._request("GET", f"/crm/objects/{settings.HUBSPOT_API_VERSION}/contacts", params=params)

    async def update_contact(self, hubspot_id: str, properties: dict[str, str | None]) -> dict:
        return await self._request("PATCH", f"/crm/objects/{settings.HUBSPOT_API_VERSION}/contacts/{hubspot_id}", json={"properties": properties})

    async def list_segments(self, after: str | None = None) -> dict:
        params = {"limit": 100, "archived": "false"}
        if after:
            params["after"] = after
        return await self._request("GET", f"/crm/lists/{settings.HUBSPOT_API_VERSION}/lists", params=params)

    async def list_memberships(self, list_id: str, after: str | None = None) -> dict:
        params = {"limit": 100}
        if after:
            params["after"] = after
        return await self._request("GET", f"/crm/lists/{settings.HUBSPOT_API_VERSION}/{list_id}/memberships", params=params)
