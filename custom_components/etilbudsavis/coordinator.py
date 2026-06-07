"""Data coordinator for eTilbudsavis."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtilbudsavisClient, EtilbudsavisApiError, EtilbudsavisAuthError
from .const import DOMAIN, CONF_TOKEN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class EtilbudsavisCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches shopping list items periodically."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, shopping_list_id: int, list_name: str = "") -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{shopping_list_id}",
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.config_entry = entry
        self.shopping_list_id = shopping_list_id
        self.list_name = list_name
        self._client = EtilbudsavisClient(
            session=async_get_clientsession(hass),
            token=entry.data[CONF_TOKEN],
        )

    @property
    def client(self) -> EtilbudsavisClient:
        return self._client

    async def _async_update_data(self) -> list[dict]:
        try:
            items = await self._client.get_shopping_list_items(self.shopping_list_id)
            if items:
                _LOGGER.debug("eTilbudsavis item fields: %s", list(items[0].keys()))
                _LOGGER.debug("eTilbudsavis first item: %s", items[0])
            return items
        except EtilbudsavisAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed("Autentifikation fejlede – log venligst ind igen") from err
        except EtilbudsavisApiError as err:
            raise UpdateFailed(f"Error fetching eTilbudsavis data: {err}") from err
