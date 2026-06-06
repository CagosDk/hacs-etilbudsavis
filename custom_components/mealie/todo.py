"""Mealie todo list entities."""
from __future__ import annotations

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
from .coordinator import MealieCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: dict[str, MealieCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MealieTodoList(coord) for coord in coordinators.values()])


class MealieTodoList(CoordinatorEntity[MealieCoordinator], TodoListEntity):
    """One Mealie shopping list as a HA todo entity."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(self, coordinator: MealieCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"mealie_{coordinator.list_id}"
        self._attr_name = coordinator.list_name or f"Mealie {coordinator.list_id}"

    @property
    def todo_items(self) -> list[TodoItem]:
        items = self.coordinator.data or []
        result = []
        for item in items:
            checked = item.get("checked", False)
            status = TodoItemStatus.COMPLETED if checked else TodoItemStatus.NEEDS_ACTION
            note = item.get("note") or ""
            food_name = (item.get("food") or {}).get("name", "")
            summary = note or food_name
            if not summary:
                continue
            result.append(TodoItem(
                uid=item["id"],
                summary=summary,
                status=status,
            ))
        result.sort(key=lambda x: (x.status == TodoItemStatus.COMPLETED, x.summary.lower()))
        return result

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.client.add_item(self.coordinator.list_id, note=item.summary)
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            await self.coordinator.client.delete_item(uid)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        checked = item.status == TodoItemStatus.COMPLETED
        current = next(
            (i for i in (self.coordinator.data or []) if i.get("id") == item.uid),
            None,
        )
        if current is None:
            return

        payload = {
            **current,
            "checked": checked,
            "note": item.summary,
        }
        await self.coordinator.client.update_item(item.uid, payload)
        await self.coordinator.async_request_refresh()
