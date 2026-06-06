"""eTilbudsavis todo list entity."""
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
    """Encode both integer id and clientId in uid field."""
    return f"{item['id']}|{item.get('clientId', '')}"


def _decode_uid(uid: str) -> tuple[int, str]:
    """Decode uid back to (integer_id, client_id)."""
    parts = uid.split("|", 1)
    return int(parts[0]), parts[1] if len(parts) > 1 else ""


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: EtilbudsavisCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EtilbudsavisTodoList(coordinator, entry)])


class EtilbudsavisTodoList(CoordinatorEntity[EtilbudsavisCoordinator], TodoListEntity):
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(self, coordinator: EtilbudsavisCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"etilbudsavis_{coordinator.shopping_list_id}"
        self._attr_name = "eTilbudsavis indkøbsliste"

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
            description = store if store else None
            result.append(TodoItem(
                uid=_encode_uid(item),
                summary=item.get("name", ""),
                status=status,
                description=description,
            ))
        # Ikke-tikkede øverst, tikkede nederst — begge grupper alfabetisk
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
        _, client_id = _decode_uid(item.uid)
        ticked = item.status == TodoItemStatus.COMPLETED
        await self.coordinator.client.tick_item(
            self.coordinator.shopping_list_id,
            client_id=client_id,
            ticked=ticked,
        )
        await self.coordinator.async_request_refresh()
