"""Mealie Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_LISTS, DOMAIN
from .coordinator import MealieCoordinator

PLATFORMS = [Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinators: dict[str, MealieCoordinator] = {}
    for sl in entry.data.get(CONF_LISTS, []):
        coordinator = MealieCoordinator(
            hass=hass,
            entry=entry,
            list_id=sl["id"],
            list_name=sl.get("name", f"Liste {sl['id']}"),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[sl["id"]] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
