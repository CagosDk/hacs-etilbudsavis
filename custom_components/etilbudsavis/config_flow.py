"""Config flow for eTilbudsavis integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
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
        """Step 1: Ask for email. Skip OTP if already authenticated."""
        errors = {}
        if user_input:
            self._email = user_input["email"]
            # Check if this email already has a config entry with a valid token
            existing = [
                e for e in self.hass.config_entries.async_entries(DOMAIN)
                if e.data.get(CONF_EMAIL) == self._email
            ]
            if existing:
                self._token = existing[0].data[CONF_TOKEN]
                _LOGGER.info("Reusing existing token for %s", self._email)
                return await self.async_step_select_list()
            # New account — do OTP flow
            client = EtilbudsavisClient(async_get_clientsession(self.hass))
            try:
                self._otp_id = await client.auth_initialize(self._email)
                return await self.async_step_otp()
            except EtilbudsavisAuthError:
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Error initializing OTP: %s", e)
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
            except EtilbudsavisAuthError:
                errors["base"] = "invalid_otp"
            except Exception as e:
                _LOGGER.exception("Error finalizing OTP: %s", e)
                errors["base"] = "unknown"
            else:
                return await self.async_step_select_list()
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_select_list(self, user_input=None):
        """Step 3: Select or enter shopping list."""
        errors = {}
        # Try to fetch lists automatically
        if not self._shopping_lists:
            try:
                client = EtilbudsavisClient(async_get_clientsession(self.hass), self._token)
                client._token = self._token
                self._shopping_lists = await client.get_shopping_lists()
            except Exception as e:
                _LOGGER.warning("Could not fetch shopping lists: %s", e)
                self._shopping_lists = []

        # Filter out lists already configured for this account
        existing_list_ids = {
            e.data.get(CONF_SHOPPING_LIST_ID)
            for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_EMAIL) == self._email
        }
        available_lists = [sl for sl in self._shopping_lists if sl["id"] not in existing_list_ids]

        if available_lists:
            if user_input:
                list_id = int(user_input["shopping_list"])
                list_name = next((sl.get("name", "Indkøbsliste") for sl in available_lists if sl["id"] == list_id), "Indkøbsliste")
                return self.async_create_entry(
                    title=f"eTilbudsavis – {list_name}",
                    data={CONF_EMAIL: self._email, CONF_TOKEN: self._token, CONF_SHOPPING_LIST_ID: list_id},
                )
            options = {str(sl["id"]): sl.get("name", f"Liste {sl['id']}") for sl in available_lists}
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
                    title=f"eTilbudsavis – Liste {list_id}",
                    data={CONF_EMAIL: self._email, CONF_TOKEN: self._token, CONF_SHOPPING_LIST_ID: list_id},
                )
            except (ValueError, TypeError):
                errors["shopping_list_id"] = "unknown"
        return self.async_show_form(
            step_id="select_list",
            data_schema=vol.Schema({vol.Required("shopping_list_id"): str}),
            errors=errors,
        )
