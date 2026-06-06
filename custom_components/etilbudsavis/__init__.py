"""eTilbudsavis Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_LISTS, CONF_SHOPPING_LIST_ID
from .coordinator import EtilbudsavisCoordinator

PLATFORMS = [Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eTilbudsavis from a config entry."""
    # Support both old format (single list) and new format (multiple lists)
    shopping_lists = entry.data.get(CONF_LISTS)
    if not shopping_lists:
        # Migration from old single-list format
        old_id = entry.data.get(CONF_SHOPPING_LIST_ID)
        if old_id:
            shopping_lists = [{"id": old_id, "name": "Indkøbsliste"}]
        else:
            shopping_lists = []

    coordinators = {}
    for sl in shopping_lists:
        coordinator = EtilbudsavisCoordinator(
            hass=hass,
            entry=entry,
            shopping_list_id=sl["id"],
            list_name=sl.get("name", f"Liste {sl['id']}"),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[sl["id"]] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
