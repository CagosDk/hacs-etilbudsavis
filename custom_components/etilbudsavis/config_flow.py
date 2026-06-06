"""Config flow for eTilbudsavis integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtilbudsavisClient, EtilbudsavisAuthError
from .const import DOMAIN, CONF_TOKEN, CONF_EMAIL, CONF_SHOPPING_LIST_ID


class EtilbudsavisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._otp_id: str = ""
        self._token: str = ""

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            self._email = user_input["email"]
            client = EtilbudsavisClient(async_get_clientsession(self.hass))
            try:
                self._otp_id = await client.auth_initialize(self._email)
                return await self.async_step_otp()
            except EtilbudsavisAuthError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required("email"): str}), errors=errors)

    async def async_step_otp(self, user_input=None):
        errors = {}
        if user_input:
            client = EtilbudsavisClient(async_get_clientsession(self.hass))
            try:
                self._token = await client.auth_finalize(self._otp_id, user_input["otp"].strip())
            except EtilbudsavisAuthError:
                errors["base"] = "invalid_otp"
            except Exception:
                errors["base"] = "unknown"
            else:
                return await self.async_step_select_list()
        return self.async_show_form(step_id="otp", data_schema=vol.Schema({vol.Required("otp"): str}), errors=errors, description_placeholders={"email": self._email})

    async def async_step_select_list(self, user_input=None):
        errors = {}
        if user_input:
            try:
                list_id = int(user_input["shopping_list_id"])
                return self.async_create_entry(title=f"eTilbudsavis – {self._email}", data={CONF_EMAIL: self._email, CONF_TOKEN: self._token, CONF_SHOPPING_LIST_ID: list_id})
            except (ValueError, TypeError):
                errors["shopping_list_id"] = "unknown"
        return self.async_show_form(step_id="select_list", data_schema=vol.Schema({vol.Required("shopping_list_id"): str}), errors=errors)
