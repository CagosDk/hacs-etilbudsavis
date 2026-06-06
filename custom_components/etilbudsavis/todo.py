"""eTilbudsavis todo list entity."""
from __future__ import annotations

from typing import Any

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eTilbudsavis todo list from config entry."""
    coordinator: EtilbudsavisCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EtilbudsavisTodoList(coordinator, entry)])


class EtilbudsavisTodoList(CoordinatorEntity[EtilbudsavisCoordinator], TodoListEntity):
    """eTilbudsavis shopping list as a HA todo entity."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: EtilbudsavisCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"etilbudsavis_{coordinator.shopping_list_id}"
        self._attr_name = "eTilbudsavis indkøbsliste"

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return current shopping list items as TodoItems."""
        items = self.coordinator.data or []
        result = []
        for item in items:
            if not item.get("isActive", True):
                continue
            status = (
                TodoItemStatus.COMPLETE
                if item.get("ticked")
                else TodoItemStatus.NEEDS_ACTION
            )
            store = (item.get("business") or {}).get("name")
            description = store if store else None
            result.append(
                TodoItem(
                    uid=str(item["id"]),
                    summary=item.get("name", ""),
                    status=status,
                    description=description,
                )
            )
        return result

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add a new item to the shopping list."""
        await self.coordinator.client.add_item(
            self.coordinator.shopping_list_id,
            name=item.summary,
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Remove items from the shopping list."""
        for uid in uids:
            await self.coordinator.client.remove_item(
                self.coordinator.shopping_list_id,
                item_id=int(uid),
            )
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Tick/untick an item."""
        ticked = item.status == TodoItemStatus.COMPLETE
        await self.coordinator.client.tick_item(
            self.coordinator.shopping_list_id,
            item_id=int(item.uid),
            ticked=ticked,
        )
        await self.coordinator.async_request_refresh()
