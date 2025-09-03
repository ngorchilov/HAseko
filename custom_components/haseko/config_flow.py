from __future__ import annotations

from typing import Any, Dict
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_API_KEY, CONF_SELECTED_SERIALS
from .coordinator import AsekoCoordinator
from .api import AsekoApi


class HasekoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}

        schema = vol.Schema({
            vol.Required(CONF_API_KEY, description={
                "description": "Enter your Aseko Cloud API key. "
                               "Create one at https://account.aseko.cloud/profile/settings/api-keys"
            }): str
        })

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        api_key = user_input[CONF_API_KEY]

        # Validate key first via /auth/check
        session = async_get_clientsession(self.hass)
        api = AsekoApi(session, api_key, "HAseko", "0.1")
        try:
            await api.auth_check()
        except Exception as e:
            msg = str(e).lower()
            errors["base"] = "invalid_auth" if ("401" in msg or "unauthorized" in msg or "forbidden" in msg) else "cannot_connect"
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        # Fetch devices to determine single vs multi
        coordinator = AsekoCoordinator(self.hass, api_key, selected_serials=None)
        data = await coordinator._async_update_data()
        units = data.get("units") or []

        choices = {u.get("serialNumber"): f"{u.get('name') or 'Unit'} ({u.get('serialNumber')})"
                   for u in units if u.get("serialNumber")}

        if len(choices) <= 1:
            return self.async_create_entry(
                title="Haseko",
                data={CONF_API_KEY: api_key, CONF_SELECTED_SERIALS: list(choices.keys()) if choices else None},
            )

        self._cached_key = api_key
        self._choices = choices
        return await self.async_step_select_devices()

    async def async_step_select_devices(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is None:
            multi = vol.Schema({
                vol.Optional(CONF_SELECTED_SERIALS, default=list(self._choices.keys())): vol.MultiSelect(self._choices)
            })
            return self.async_show_form(step_id="select_devices", data_schema=multi, errors=errors)

        selected = user_input.get(CONF_SELECTED_SERIALS) or list(self._choices.keys())
        return self.async_create_entry(
            title="Haseko",
            data={CONF_API_KEY: self._cached_key, CONF_SELECTED_SERIALS: selected},
        )
