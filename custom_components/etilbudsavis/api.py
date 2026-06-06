"""eTilbudsavis API client."""
from __future__ import annotations

import base64
import json
import uuid
from typing import Any

import aiohttp

API_KEY = "152000596c6e45d9983eab0c14afebea"
BASE_URL = "https://etilbudsavis.dk"


class EtilbudsavisAuthError(Exception):
    """Raised when authentication fails."""


class EtilbudsavisApiError(Exception):
    """Raised when an API call fails."""


class EtilbudsavisClient:
    """Async API client for eTilbudsavis."""

    def __init__(self, session: aiohttp.ClientSession, token: str | None = None) -> None:
        self._session = session
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/indkoebslister/aktiv",
            "x-api-key": API_KEY,
            "user-agent": "Mozilla/5.0 (compatible; HomeAssistant/eTilbudsavis)",
        }
        if self._token:
            cookie_value = json.dumps({"token": self._token})
            headers["Cookie"] = f"tjek-session={cookie_value}"
        return headers

    # --- Auth ---

    async def auth_initialize(self, email: str) -> str:
        """Step 1: Send OTP to email. Returns otpId."""
        payload = {"apiKey": API_KEY, "email": email}
        async with self._session.post(
            f"{BASE_URL}/api/auth-otp-initialize",
            json=payload,
            headers=self._headers,
        ) as resp:
            if resp.status != 200:
                raise EtilbudsavisAuthError(f"Failed to initialize OTP: {resp.status}")
            data = await resp.json()
            return data["otpId"]

    async def auth_finalize(self, otp_id: str, otp: str) -> str:
        """Step 2: Verify OTP. Returns session token."""
        payload = {"apiKey": API_KEY, "otpId": otp_id, "otp": otp}
        async with self._session.post(
            f"{BASE_URL}/api/auth-otp-finalize",
            json=payload,
            headers=self._headers,
        ) as resp:
            if resp.status != 200:
                raise EtilbudsavisAuthError(f"Invalid OTP: {resp.status}")
            data = await resp.json()
            token = data.get("token")
            if not token:
                raise EtilbudsavisAuthError("No token in response")
            self._token = token
            return token

    # --- Shopping list ---

    async def get_shopping_lists(self) -> list[dict]:
        """Get all shopping lists for the user."""
        key = self._make_key("shoppingLists", {})
        data = await self._rpc([key])
        return data[0].get("value", [])

    async def get_shopping_list_items(self, shopping_list_id: int) -> list[dict]:
        """Get items in a shopping list."""
        key = self._make_key("shoppingListItems", {"shoppingListId": shopping_list_id})
        data = await self._rpc([key])
        return data[0].get("value", [])

    async def add_item(self, shopping_list_id: int, name: str, count: int = 1) -> dict:
        """Add an item to a shopping list."""
        payload = {
            "shoppingListId": shopping_list_id,
            "item": {
                "clientId": str(uuid.uuid4()),
                "name": name,
                "count": count,
            },
        }
        async with self._session.post(
            f"{BASE_URL}/api/shopping-list-add-item",
            json=payload,
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"Failed to add item: {resp.status}")
            return await resp.json()

    async def remove_item(self, shopping_list_id: int, item_id: int) -> None:
        """Remove an item from a shopping list."""
        payload = {
            "shoppingListId": shopping_list_id,
            "itemId": item_id,
        }
        async with self._session.post(
            f"{BASE_URL}/api/shopping-list-remove-item",
            json=payload,
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"Failed to remove item: {resp.status}")

    async def tick_item(self, shopping_list_id: int, item_id: int, ticked: bool) -> None:
        """Tick/untick an item on the shopping list."""
        payload = {
            "shoppingListId": shopping_list_id,
            "itemId": item_id,
            "ticked": ticked,
        }
        async with self._session.post(
            f"{BASE_URL}/api/shopping-list-tick-item",
            json=payload,
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"Failed to tick item: {resp.status}")

    # --- Helpers ---

    def _make_key(self, query_name: str, params: dict) -> str:
        payload = json.dumps([query_name, params], separators=(",", ":"))
        return base64.b64encode(payload.encode()).decode()

    async def _rpc(self, keys: list[str]) -> list[dict[str, Any]]:
        async with self._session.post(
            f"{BASE_URL}/",
            json={"data": keys},
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"RPC failed: {resp.status}")
            return await resp.json()
