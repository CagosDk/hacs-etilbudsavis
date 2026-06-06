"""Mealie API client."""
from __future__ import annotations

from typing import Any

import aiohttp


class MealieAuthError(Exception):
    pass


class MealieApiError(Exception):
    pass


class MealieClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_token: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    async def validate(self) -> dict[str, Any]:
        """Validate credentials by calling the user self endpoint."""
        async with self._session.get(
            f"{self._base_url}/api/users/self", headers=self._headers
        ) as resp:
            if resp.status == 401:
                raise MealieAuthError("Invalid API token")
            if not resp.ok:
                raise MealieApiError(f"Cannot connect to Mealie: {resp.status}")
            return await resp.json()

    async def get_shopping_lists(self) -> list[dict]:
        async with self._session.get(
            f"{self._base_url}/api/groups/shopping/lists",
            headers=self._headers,
            params={"perPage": -1},
        ) as resp:
            if resp.status == 401:
                raise MealieAuthError("Invalid API token")
            if not resp.ok:
                raise MealieApiError(f"Failed to get shopping lists: {resp.status}")
            data = await resp.json()
            return data.get("items", [])

    async def get_shopping_list_items(self, list_id: str) -> list[dict]:
        async with self._session.get(
            f"{self._base_url}/api/groups/shopping/lists/{list_id}",
            headers=self._headers,
        ) as resp:
            if resp.status == 401:
                raise MealieAuthError("Invalid API token")
            if not resp.ok:
                raise MealieApiError(f"Failed to get shopping list: {resp.status}")
            data = await resp.json()
            return data.get("listItems", [])

    async def add_item(self, list_id: str, note: str) -> dict:
        payload = {"shoppingListId": list_id, "note": note, "isFood": False, "checked": False}
        async with self._session.post(
            f"{self._base_url}/api/groups/shopping/items",
            json=payload,
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise MealieApiError(f"Failed to add item: {resp.status}")
            return await resp.json()

    async def update_item(self, item_id: str, payload: dict) -> dict:
        async with self._session.put(
            f"{self._base_url}/api/groups/shopping/items/{item_id}",
            json=payload,
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise MealieApiError(f"Failed to update item: {resp.status}")
            return await resp.json()

    async def delete_item(self, item_id: str) -> None:
        async with self._session.delete(
            f"{self._base_url}/api/groups/shopping/items/{item_id}",
            headers=self._headers,
        ) as resp:
            if not resp.ok:
                raise MealieApiError(f"Failed to delete item: {resp.status}")
