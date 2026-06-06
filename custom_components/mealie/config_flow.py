"""Config flow for Mealie integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import MealieApiError, MealieAuthError, MealieClient
from .const import CONF_API_TOKEN, CONF_BASE_URL, CONF_LISTS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MealieConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str = ""
        self._api_token: str = ""
        self._available_lists: list[dict] = []

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input:
            self._base_url = user_input[CONF_BASE_URL].rstrip("/")
            self._api_token = user_input[CONF_API_TOKEN].strip()
            client = MealieClient(async_get_clientsession(self.hass), self._base_url, self._api_token)
            try:
                await client.validate()
                return await self.async_step_select_lists()
            except MealieAuthError:
                errors["base"] = "invalid_auth"
            except MealieApiError:
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.exception("Unexpected error connecting to Mealie: %s", exc)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_API_TOKEN): str,
            }),
            errors=errors,
        )

    async def async_step_select_lists(self, user_input=None):
        errors: dict[str, str] = {}
        if not self._available_lists:
            try:
                client = MealieClient(async_get_clientsession(self.hass), self._base_url, self._api_token)
                all_lists = await client.get_shopping_lists()
                existing_ids = {
                    sl["id"]
                    for e in self.hass.config_entries.async_entries(DOMAIN)
                    for sl in e.data.get(CONF_LISTS, [])
                }
                self._available_lists = [sl for sl in all_lists if sl["id"] not in existing_ids]
            except Exception as exc:
                _LOGGER.warning("Could not fetch Mealie shopping lists: %s", exc)
                self._available_lists = []

        if self._available_lists:
            options = [
                SelectOptionDict(value=sl["id"], label=sl.get("name", f"Liste {sl['id']}"))
                for sl in self._available_lists
            ]
            if user_input:
                selected_ids = user_input.get("shopping_lists", [])
                if not isinstance(selected_ids, list):
                    selected_ids = [selected_ids]
                selected = [sl for sl in self._available_lists if sl["id"] in selected_ids]
                if selected:
                    return self._create_entry(selected)
                errors["base"] = "no_list_selected"
            return self.async_show_form(
                step_id="select_lists",
                data_schema=vol.Schema({
                    vol.Required("shopping_lists"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }),
                errors=errors,
            )

        # Fallback: no lists found
        return self.async_abort(reason="no_lists_available")

    async def async_step_reauth(self, entry_data) -> config_entries.FlowResult:
        self._base_url = entry_data.get(CONF_BASE_URL, "")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input:
            self._api_token = user_input[CONF_API_TOKEN].strip()
            client = MealieClient(async_get_clientsession(self.hass), self._base_url, self._api_token)
            try:
                await client.validate()
            except MealieAuthError:
                errors["base"] = "invalid_auth"
            except Exception as exc:
                _LOGGER.exception("Error during Mealie reauth: %s", exc)
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_API_TOKEN: self._api_token}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
            description_placeholders={CONF_BASE_URL: self._base_url},
            errors=errors,
        )

    def _create_entry(self, shopping_lists: list[dict]) -> config_entries.FlowResult:
        return self.async_create_entry(
            title=f"Mealie – {self._base_url}",
            data={
                CONF_BASE_URL: self._base_url,
                CONF_API_TOKEN: self._api_token,
                CONF_LISTS: [{"id": sl["id"], "name": sl.get("name", sl["id"])} for sl in shopping_lists],
            },
        )
