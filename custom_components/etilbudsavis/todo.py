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


def _encode_uid(item: dict) -> str:
    return f"{item['id']}|{item.get('clientId', '')}"


def _decode_uid(uid: str) -> tuple[int, str]:
    parts = uid.split("|", 1)
    return int(parts[0]), parts[1] if len(parts) > 1 else ""


def _parse_summary(summary: str) -> tuple[int, str, str]:
    """Extract (count, name, short_desc) from '{N}x {name} (note)' format."""
    match = re.search(r'(\d+)x\s+(.+)$', summary)
    raw = match.group(2).strip() if match else summary.strip()
    count = int(match.group(1)) if match else 1
    note_match = re.search(r'^(.*?)\s*\(([^)]+)\)$', raw)
    if note_match:
        return count, note_match.group(1).strip(), note_match.group(2).strip()
    return count, raw, ""


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
    if (valid_until - now).days < 0:
        return "UDLØBET!!! "
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
        count, name, short_desc = _parse_summary(item.summary)
        await self.coordinator.client.add_item(
            self.coordinator.shopping_list_id, name=name, count=count, short_desc=short_desc
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
        new_count, new_name, new_short_desc = _parse_summary(item.summary)

        current = next(
            (i for i in (self.coordinator.data or []) if i.get("id") == item_id),
            None,
        )
        current_name = (current or {}).get("name", "")

        if new_name != current_name:
            # Kun navneændring kræver slet+opret
            await self.coordinator.client.remove_item(
                self.coordinator.shopping_list_id, item_id=item_id
            )
            new_item = await self.coordinator.client.add_item(
                self.coordinator.shopping_list_id,
                name=new_name,
                count=new_count,
                short_desc=new_short_desc,
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
            # Antal, note og afkrydsning kan opdateres direkte
            await self.coordinator.client.tick_item(
                self.coordinator.shopping_list_id,
                client_id=client_id,
                ticked=ticked,
                count=new_count,
                short_desc=new_short_desc,
            )

        await self.coordinator.async_request_refresh()
