"""eTilbudsavis API client."""
from __future__ import annotations

import base64
import json
import uuid
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import aiohttp

API_KEY = "152000596c6e45d9983eab0c14afebea"
BASE_URL = "https://etilbudsavis.dk"


class EtilbudsavisAuthError(Exception):
    pass


class EtilbudsavisApiError(Exception):
    pass


class EtilbudsavisClient:
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
            cookie_value = urllib.parse.quote(json.dumps({"token": self._token}, separators=(",", ":")))
            headers["Cookie"] = f"tjek-session={cookie_value}"
        return headers

    async def auth_initialize(self, email: str) -> str:
        payload = {"apiKey": API_KEY, "email": email}
        async with self._session.post(f"{BASE_URL}/api/auth-otp-initialize", json=payload, headers=self._headers) as resp:
            if resp.status != 200:
                raise EtilbudsavisAuthError(f"Failed to initialize OTP: {resp.status}")
            return (await resp.json())["otpId"]

    async def auth_finalize(self, otp_id: str, otp: str) -> str:
        payload = {"apiKey": API_KEY, "otpId": otp_id, "otp": otp}
        async with self._session.post(f"{BASE_URL}/api/auth-otp-finalize", json=payload, headers=self._headers) as resp:
            if resp.status != 200:
                raise EtilbudsavisAuthError(f"Invalid OTP: {resp.status}")
            data = await resp.json()
            token = data.get("token")
            if not token:
                raise EtilbudsavisAuthError("No token in response")
            self._token = token
            return token

    async def get_shopping_lists(self) -> list[dict]:
        key = self._make_key("shoppingLists", {})
        data = await self._rpc([key])
        return data[0].get("value", []) if data else []

    async def get_shopping_list_items(self, shopping_list_id: int) -> list[dict]:
        key = self._make_key("shoppingListItems", {"shoppingListId": shopping_list_id})
        data = await self._rpc([key])
        return data[0].get("value", []) if data else []

    async def add_item(self, shopping_list_id: int, name: str, count: int = 1, short_desc: str = "") -> dict:
        client_id = str(uuid.uuid4())
        item: dict = {"clientId": client_id, "name": name, "count": count}
        if short_desc:
            item["shortDescription"] = short_desc
        payload = {"shoppingListId": shopping_list_id, "item": item}
        async with self._session.post(f"{BASE_URL}/api/shopping-list-add-item", json=payload, headers=self._headers) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"Failed to add item: {resp.status}")
            result = await resp.json()
            if isinstance(result, dict):
                result.setdefault("clientId", client_id)
            return result

    async def remove_item(self, shopping_list_id: int, item_id: int) -> None:
        payload = {"shoppingListId": shopping_list_id, "itemId": item_id}
        async with self._session.post(f"{BASE_URL}/api/shopping-list-remove-item", json=payload, headers=self._headers) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"Failed to remove item: {resp.status}")

    async def tick_item(self, shopping_list_id: int, client_id: str, ticked: bool, count: int | None = None, short_desc: str | None = None) -> None:
        _now = datetime.now(timezone.utc)
        updated_at = _now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{_now.microsecond // 1000:03d}Z"
        item: dict = {"clientId": client_id, "ticked": ticked, "updatedAt": updated_at}
        if count is not None:
            item["count"] = count
        if short_desc is not None:
            item["shortDescription"] = short_desc
        payload = {"shoppingListId": shopping_list_id, "item": item}
        async with self._session.post(f"{BASE_URL}/api/shopping-list-update-item", json=payload, headers=self._headers) as resp:
            if not resp.ok:
                raise EtilbudsavisApiError(f"Failed to tick item: {resp.status}")

    def _make_key(self, query_name: str, params: dict) -> str:
        payload = json.dumps([query_name, params], separators=(",", ":"))
        return base64.b64encode(payload.encode()).decode()

    async def _rpc(self, keys: list[str]) -> list[dict[str, Any]]:
        async with self._session.post(f"{BASE_URL}/", json={"data": keys}, headers=self._headers) as resp:
            if resp.status == 401:
                raise EtilbudsavisAuthError("Token udløbet eller ugyldigt")
            if not resp.ok:
                raise EtilbudsavisApiError(f"RPC failed: {resp.status}")
            data = await resp.json()
            if isinstance(data, dict):
                return [data]
            return data
