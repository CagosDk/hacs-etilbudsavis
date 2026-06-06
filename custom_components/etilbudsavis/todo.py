"""eTilbudsavis todo list entities."""
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
from .coordinator import EtilbudsavisCoordinator


def _encode_uid(item: dict) -> str:
    return f"{item['id']}|{item.get('clientId', '')}"


def _decode_uid(uid: str) -> tuple[int, str]:
    parts = uid.split("|", 1)
    return int(parts[0]), parts[1] if len(parts) > 1 else ""


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up one todo entity per shopping list."""
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
        result = []
        for item in items:
            if not item.get("isActive", True):
                continue
            ticked = item.get("ticked", False)
            status = TodoItemStatus.COMPLETED if ticked else TodoItemStatus.NEEDS_ACTION
            store = (item.get("business") or {}).get("name")
            result.append(TodoItem(
                uid=_encode_uid(item),
                summary=item.get("name", ""),
                status=status,
                description=store,
            ))
        result.sort(key=lambda x: (x.status == TodoItemStatus.COMPLETED, x.summary.lower()))
        return result

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.client.add_item(self.coordinator.shopping_list_id, name=item.summary)
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
        name_changed = bool(
            current and item.summary and item.summary != current.get("name", "")
        )

        if name_changed:
            await self.coordinator.client.remove_item(
                self.coordinator.shopping_list_id, item_id=item_id
            )
            new_item = await self.coordinator.client.add_item(
                self.coordinator.shopping_list_id, name=item.summary
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
