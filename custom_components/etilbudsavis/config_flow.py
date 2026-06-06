"""Config flow for eTilbudsavis integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtilbudsavisClient, EtilbudsavisAuthError
from .const import DOMAIN, CONF_TOKEN, CONF_EMAIL, CONF_LISTS

_LOGGER = logging.getLogger(__name__)


class EtilbudsavisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for eTilbudsavis."""

    VERSION = 2

    def __init__(self) -> None:
        self._email: str = ""
        self._otp_id: str = ""
        self._token: str = ""
        self._available_lists: list[dict] = []

    async def async_step_user(self, user_input=None):
        """Step 1: Ask for email."""
        errors = {}
        if user_input:
            self._email = user_input["email"]
            # Check if this email already has a config entry
            existing = [
                e for e in self.hass.config_entries.async_entries(DOMAIN)
                if e.data.get(CONF_EMAIL) == self._email
            ]
            if existing:
                # Reuse existing token - go straight to list selection
                self._token = existing[0].data[CONF_TOKEN]
                return await self.async_step_select_lists()
            # New account - do OTP flow
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
                return await self.async_step_select_lists()
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_select_lists(self, user_input=None):
        """Step 3: Select which lists to add."""
        errors = {}
        # Fetch available lists
        if not self._available_lists:
            try:
                client = EtilbudsavisClient(async_get_clientsession(self.hass), self._token)
                all_lists = await client.get_shopping_lists()
                # Get already configured list IDs for this account
                existing_ids = {
                    lid
                    for e in self.hass.config_entries.async_entries(DOMAIN)
                    if e.data.get(CONF_EMAIL) == self._email
                    for sl in e.data.get(CONF_LISTS, [])
                    for lid in [sl["id"]]
                }
                self._available_lists = [sl for sl in all_lists if sl["id"] not in existing_ids]
            except Exception as e:
                _LOGGER.warning("Could not fetch shopping lists: %s", e)
                self._available_lists = []

        if self._available_lists:
            if user_input:
                selected_ids = user_input.get("shopping_lists", [])
                if not selected_ids:
                    errors["base"] = "no_list_selected"
                else:
                    selected = [sl for sl in self._available_lists if str(sl["id"]) in selected_ids]
                    return self._create_entry(selected)
            options = {str(sl["id"]): sl.get("name", f"Liste {sl['id']}") for sl in self._available_lists}
            return self.async_show_form(
                step_id="select_lists",
                data_schema=vol.Schema({
                    vol.Required("shopping_lists"): vol.All(
                        cv_multi_select(options), vol.Length(min=1)
                    )
                }),
                errors=errors,
            )
        # Fallback: manual ID + name
        if user_input:
            try:
                list_id = int(user_input["shopping_list_id"])
                list_name = user_input.get("list_name", f"Liste {list_id}").strip() or f"Liste {list_id}"
                return self._create_entry([{"id": list_id, "name": list_name}])
            except (ValueError, TypeError):
                errors["shopping_list_id"] = "unknown"
        return self.async_show_form(
            step_id="select_lists",
            data_schema=vol.Schema({
                vol.Required("shopping_list_id"): str,
                vol.Optional("list_name"): str,
            }),
            errors=errors,
        )

    def _create_entry(self, shopping_lists: list[dict]):
        # Check if we already have an entry for this account - update it
        existing = [
            e for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_EMAIL) == self._email
        ]
        if existing:
            entry = existing[0]
            current_lists = list(entry.data.get(CONF_LISTS, []))
            current_lists.extend(shopping_lists)
            self.hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_LISTS: current_lists, CONF_TOKEN: self._token},
            )
            return self.async_abort(reason="updated_existing")
        # New entry
        title = f"eTilbudsavis – {self._email}"
        return self.async_create_entry(
            title=title,
            data={
                CONF_EMAIL: self._email,
                CONF_TOKEN: self._token,
                CONF_LISTS: shopping_lists,
            },
        )


def cv_multi_select(options: dict):
    """Validate multi-select input."""
    def _validate(value):
        if isinstance(value, list):
            for v in value:
                if v not in options:
                    raise vol.Invalid(f"Invalid option: {v}")
            return value
        raise vol.Invalid("Expected a list")
    return _validate
