"""eTilbudsavis todo list entities."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EtilbudsavisCoordinator

_DANISH_DAYS = ["MANDAG", "TIRSDAG", "ONSDAG", "TORSDAG", "FREDAG", "LØRDAG", "SØNDAG"]


def _encode_uid(item: dict) -> str:
    return f"{item['id']}|{item.get('clientId', '')}"


def _decode_uid(uid: str) -> tuple[int, str]:
    parts = uid.split("|", 1)
    return int(parts[0]), parts[1] if len(parts) > 1 else ""


def _parse_summary(summary: str, short_desc: str = "") -> tuple[int, str]:
    """Extract count and name, stripping expiry prefix and known shortDescription note."""
    match = re.search(r'(\d+)x\s+(.+)$', summary)
    raw_name = match.group(2).strip() if match else summary.strip()
    count = int(match.group(1)) if match else 1
    if short_desc and raw_name.endswith(f"({short_desc})"):
        raw_name = raw_name[:-(len(short_desc) + 2)].strip()
    return count, raw_name


def _expiry_prefix(offer: dict | None, now: datetime) -> str:
    if not offer:
        return ""
    valid_until_str = offer.get("validUntil")
    if not valid_until_str:
        return ""
    try:
        valid_until = datetime.fromisoformat(valid_until_str.replace("Z", "+00:00"))
    except ValueError:
        return ""
    delta = (valid_until - now).days
    day = _DANISH_DAYS[valid_until.weekday()]
    if delta < 0:
        return f"UDLØB {day}!!! "
    if delta <= 2:
        return f"UDLØBER {day}! "
    return ""


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinators: dict[int, EtilbudsavisCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EtilbudsavisTodoList(coord) for coord in coordinators.values()])


class EtilbudsavisTodoList(CoordinatorEntity[EtilbudsavisCoordinator], TodoListEntity):
    """One eTilbudsavis shopping list as a HA todo entity."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(self, coordinator: EtilbudsavisCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"etilbudsavis_{coordinator.shopping_list_id}"
        self._attr_name = coordinator.list_name or f"eTilbudsavis {coordinator.shopping_list_id}"

    @property
    def todo_items(self) -> list[TodoItem]:
        items = self.coordinator.data or []
        now = datetime.now(timezone.utc)
        result = []
        for item in items:
            if not item.get("isActive", True):
                continue
            ticked = item.get("ticked", False)
            status = TodoItemStatus.COMPLETED if ticked else TodoItemStatus.NEEDS_ACTION

            count = item.get("count") or 1
            name = item.get("name", "")
            short_desc = item.get("shortDescription") or ""
            store = (item.get("business") or {}).get("name") or ""
            prefix = _expiry_prefix(item.get("offer"), now)

            summary = f"{prefix}{count}x {name}"
            if short_desc:
                summary += f" ({short_desc})"
            description = store or None

            result.append(TodoItem(
                uid=_encode_uid(item),
                summary=summary,
                status=status,
                description=description,
            ))
        result.sort(key=lambda x: (x.status == TodoItemStatus.COMPLETED, x.summary.lower()))
        return result

    async def async_create_todo_item(self, item: TodoItem) -> None:
        count, name = _parse_summary(item.summary)
        await self.coordinator.client.add_item(
            self.coordinator.shopping_list_id, name=name, count=count
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            item_id, _ = _decode_uid(uid)
            await self.coordinator.client.remove_item(self.coordinator.shopping_list_id, item_id=item_id)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        item_id, client_id = _decode_uid(item.uid)
        ticked = item.status == TodoItemStatus.COMPLETED

        current = next(
            (i for i in (self.coordinator.data or []) if i.get("id") == item_id),
            None,
        )
        current_name = (current or {}).get("name", "")
        current_count = (current or {}).get("count") or 1
        current_short_desc = (current or {}).get("shortDescription") or ""
        new_count, new_name = _parse_summary(item.summary, current_short_desc)

        if new_name != current_name or new_count != current_count:
            await self.coordinator.client.remove_item(
                self.coordinator.shopping_list_id, item_id=item_id
            )
            new_item = await self.coordinator.client.add_item(
                self.coordinator.shopping_list_id, name=new_name, count=new_count
            )
            if ticked:
                new_client_id = new_item.get("clientId", "")
                if new_client_id:
                    await self.coordinator.client.tick_item(
                        self.coordinator.shopping_list_id,
                        client_id=new_client_id,
                        ticked=True,
                    )
        else:
            await self.coordinator.client.tick_item(
                self.coordinator.shopping_list_id,
                client_id=client_id,
                ticked=ticked,
            )

        await self.coordinator.async_request_refresh()
