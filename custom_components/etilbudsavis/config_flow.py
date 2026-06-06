"""Config flow for eTilbudsavis integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .api import EtilbudsavisClient, EtilbudsavisAuthError
from .const import DOMAIN, CONF_TOKEN, CONF_EMAIL, CONF_LISTS

_LOGGER = logging.getLogger(__name__)


class EtilbudsavisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._email: str = ""
        self._otp_id: str = ""
        self._token: str = ""
        self._available_lists: list[dict] = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            self._email = user_input["email"]
            existing = [
                e for e in self.hass.config_entries.async_entries(DOMAIN)
                if e.data.get(CONF_EMAIL) == self._email
            ]
            if existing:
                self._token = existing[0].data[CONF_TOKEN]
                return await self.async_step_select_lists()
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
        errors = {}
        if not self._available_lists:
            try:
                client = EtilbudsavisClient(async_get_clientsession(self.hass), self._token)
                all_lists = await client.get_shopping_lists()
                existing_ids = {
                    sl["id"]
                    for e in self.hass.config_entries.async_entries(DOMAIN)
                    if e.data.get(CONF_EMAIL) == self._email
                    for sl in e.data.get(CONF_LISTS, [])
                }
                self._available_lists = [sl for sl in all_lists if sl["id"] not in existing_ids]
            except Exception as e:
                _LOGGER.warning("Could not fetch shopping lists: %s", e)
                self._available_lists = []

        if self._available_lists:
            options = [
                SelectOptionDict(value=str(sl["id"]), label=sl.get("name", f"Liste {sl['id']}"))
                for sl in self._available_lists
            ]
            if user_input:
                selected_ids = user_input.get("shopping_lists", [])
                if not isinstance(selected_ids, list):
                    selected_ids = [selected_ids]
                selected = [sl for sl in self._available_lists if str(sl["id"]) in selected_ids]
                if selected:
                    return await self._async_create_entry(selected)
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

        # Fallback: manual entry
        if user_input:
            try:
                list_id = int(user_input["shopping_list_id"])
                list_name = (user_input.get("list_name") or f"Liste {list_id}").strip()
                return await self._async_create_entry([{"id": list_id, "name": list_name}])
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

    async def async_step_reauth(self, entry_data) -> config_entries.FlowResult:
        """Token udløbet — send ny OTP og bed brugeren bekræfte."""
        self._email = entry_data.get(CONF_EMAIL, "")
        client = EtilbudsavisClient(async_get_clientsession(self.hass))
        try:
            self._otp_id = await client.auth_initialize(self._email)
        except EtilbudsavisAuthError:
            return self.async_abort(reason="cannot_connect")
        except Exception as e:
            _LOGGER.exception("Fejl ved re-auth OTP-initialisering: %s", e)
            return self.async_abort(reason="unknown")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> config_entries.FlowResult:
        errors = {}
        if user_input:
            client = EtilbudsavisClient(async_get_clientsession(self.hass))
            try:
                self._token = await client.auth_finalize(self._otp_id, user_input["otp"].strip())
            except EtilbudsavisAuthError:
                errors["base"] = "invalid_otp"
            except Exception as e:
                _LOGGER.exception("Fejl ved re-auth OTP-bekræftelse: %s", e)
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_TOKEN: self._token}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            description_placeholders={"email": self._email},
            errors=errors,
        )

    async def _async_create_entry(self, shopping_lists: list[dict]):
        existing = [
            e for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_EMAIL) == self._email
        ]
        if existing:
            entry = existing[0]
            current = list(entry.data.get(CONF_LISTS, []))
            current.extend(shopping_lists)
            self.hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_LISTS: current, CONF_TOKEN: self._token},
            )
            # Reload the entry so new entities are created immediately
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(entry.entry_id)
            )
            return self.async_abort(reason="updated_existing")
        return self.async_create_entry(
            title=f"eTilbudsavis \u2013 {self._email}",
            data={CONF_EMAIL: self._email, CONF_TOKEN: self._token, CONF_LISTS: shopping_lists},
        )
