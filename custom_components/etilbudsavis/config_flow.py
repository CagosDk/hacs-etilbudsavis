"""Config flow for eTilbudsavis integration."""
from __future__ import annotations

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtilbudsavisClient, EtilbudsavisAuthError
from .const import DOMAIN, CONF_TOKEN, CONF_EMAIL, CONF_SHOPPING_LIST_ID, CONF_OTP_ID


class EtilbudsavisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for eTilbudsavis."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._otp_id: str = ""
        self._token: str = ""
        self._shopping_lists: list[dict] = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Step 1: Ask for email and send OTP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input["email"]
            session = async_get_clientsession(self.hass)
            client = EtilbudsavisClient(session)
            try:
                self._otp_id = await client.auth_initialize(self._email)
                return await self.async_step_otp()
            except EtilbudsavisAuthError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("email"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_otp(self, user_input: dict | None = None) -> FlowResult:
        """Step 2: Ask for OTP code from email."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = EtilbudsavisClient(session)
            try:
                self._token = await client.auth_finalize(
                    self._otp_id, user_input["otp"].strip()
                )
                # Fetch shopping lists to find active one
                self._shopping_lists = await client.get_shopping_lists()
                if not self._shopping_lists:
                    errors["base"] = "no_shopping_list"
                elif len(self._shopping_lists) == 1:
                    # Only one list — skip selection step
                    sl = self._shopping_lists[0]
                    return self._create_entry(sl["id"], sl.get("name", "Indkøbsliste"))
                else:
                    return await self.async_step_select_list()
            except EtilbudsavisAuthError:
                errors["base"] = "invalid_otp"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_select_list(self, user_input: dict | None = None) -> FlowResult:
        """Step 3 (optional): Select which shopping list to use."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_id = int(user_input["shopping_list"])
            selected = next(
                (sl for sl in self._shopping_lists if sl["id"] == selected_id),
                self._shopping_lists[0],
            )
            return self._create_entry(selected["id"], selected.get("name", "Indkøbsliste"))

        list_options = {
            str(sl["id"]): sl.get("name", f"Liste {sl['id']}")
            for sl in self._shopping_lists
        }

        return self.async_show_form(
            step_id="select_list",
            data_schema=vol.Schema(
                {vol.Required("shopping_list"): vol.In(list_options)}
            ),
            errors=errors,
        )

    def _create_entry(self, shopping_list_id: int, list_name: str) -> FlowResult:
        return self.async_create_entry(
            title=f"eTilbudsavis – {self._email}",
            data={
                CONF_EMAIL: self._email,
                CONF_TOKEN: self._token,
                CONF_SHOPPING_LIST_ID: shopping_list_id,
            },
        )
