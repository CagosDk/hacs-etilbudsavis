"""Config flow for eTilbudsavis integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtilbudsavisClient, EtilbudsavisAuthError
from .const import DOMAIN, CONF_TOKEN, CONF_EMAIL, CONF_SHOPPING_LIST_ID

_LOGGER = logging.getLogger(__name__)


class EtilbudsavisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for eTilbudsavis."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._otp_id: str = ""
        self._token: str = ""
        self._shopping_lists: list[dict] = []

    async def async_step_user(self, user_input=None):
        """Step 1: Ask for email and send OTP."""
        errors = {}
        if user_input:
            self._email = user_input["email"]
            client = EtilbudsavisClient(async_get_clientsession(self.hass))
            try:
                self._otp_id = await client.auth_initialize(self._email)
                return await self.async_step_otp()
            except EtilbudsavisAuthError:
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Unexpected error initializing OTP: %s", e)
                errors["base"] = "unknown"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("email"): str}),
            errors=errors,
        )

    async def async_step_otp(self, user_input=None):
        """Step 2: Verify OTP code."""
        errors = {}
        if user_input:
            client = EtilbudsavisClient(async_get_clientsession(self.hass))
            try:
                self._token = await client.auth_finalize(
                    self._otp_id, user_input["otp"].strip()
                )
                client._token = self._token
                # Try to fetch shopping lists automatically
                try:
                    self._shopping_lists = await client.get_shopping_lists()
                except Exception as e:
                    _LOGGER.warning("Could not fetch shopping lists: %s", e)
                    self._shopping_lists = []
                return await self.async_step_select_list()
            except EtilbudsavisAuthError:
                errors["base"] = "invalid_otp"
            except Exception as e:
                _LOGGER.exception("Unexpected error finalizing OTP: %s", e)
                errors["base"] = "unknown"
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_select_list(self, user_input=None):
        """Step 3: Select or enter shopping list."""
        errors = {}
        # If we have lists from auto-discovery, show a dropdown
        if self._shopping_lists:
            if user_input:
                list_id = int(user_input["shopping_list"])
                name = next(
                    (sl.get("name", "Indkøbsliste") for sl in self._shopping_lists if sl["id"] == list_id),
                    "Indkøbsliste",
                )
                return self.async_create_entry(
                    title=f"eTilbudsavis \u2013 {self._email}",
                    data={CONF_EMAIL: self._email, CONF_TOKEN: self._token, CONF_SHOPPING_LIST_ID: list_id},
                )
            options = {str(sl["id"]): sl.get("name", f"Liste {sl['id']}") for sl in self._shopping_lists}
            return self.async_show_form(
                step_id="select_list",
                data_schema=vol.Schema({vol.Required("shopping_list"): vol.In(options)}),
                errors=errors,
            )
        # Fallback: manual ID entry
        if user_input:
            try:
                list_id = int(user_input["shopping_list_id"])
                return self.async_create_entry(
                    title=f"eTilbudsavis \u2013 {self._email}",
                    data={CONF_EMAIL: self._email, CONF_TOKEN: self._token, CONF_SHOPPING_LIST_ID: list_id},
                )
            except (ValueError, TypeError):
                errors["shopping_list_id"] = "unknown"
        return self.async_show_form(
            step_id="select_list",
            data_schema=vol.Schema({vol.Required("shopping_list_id"): str}),
            errors=errors,
        )
