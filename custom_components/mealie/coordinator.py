"""Data coordinator for Mealie."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MealieApiError, MealieAuthError, MealieClient
from .const import CONF_API_TOKEN, CONF_BASE_URL, DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class MealieCoordinator(DataUpdateCoordinator):
    """Fetches items for one Mealie shopping list."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        list_id: str,
        list_name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{list_id}",
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.config_entry = entry
        self.list_id = list_id
        self.list_name = list_name
        self._client = MealieClient(
            session=async_get_clientsession(hass),
            base_url=entry.data[CONF_BASE_URL],
            api_token=entry.data[CONF_API_TOKEN],
        )

    @property
    def client(self) -> MealieClient:
        return self._client

    async def _async_update_data(self) -> list[dict]:
        try:
            return await self._client.get_shopping_list_items(self.list_id)
        except MealieAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed("Mealie API-token er ugyldigt – log venligst ind igen") from err
        except MealieApiError as err:
            raise UpdateFailed(f"Fejl ved hentning af Mealie-data: {err}") from err
