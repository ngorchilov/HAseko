from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import UPDATE_INTERVAL, DEFAULT_CLIENT_NAME, DEFAULT_CLIENT_VERSION, DOMAIN
from .api import AsekoApi

_LOGGER = logging.getLogger(__name__)


class AsekoCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api_key: str, selected_serials: Optional[List[str]]) -> None:
        super().__init__(hass, _LOGGER, name="AsekoCoordinator", update_interval=UPDATE_INTERVAL)
        session = async_get_clientsession(hass)
        self.api = AsekoApi(session, api_key, DEFAULT_CLIENT_NAME, DEFAULT_CLIENT_VERSION)
        self.selected_serials = selected_serials  # None -> include all

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            units_resp = await self.api.list_units(page=1, limit=100)
            units = units_resp.get("items") or []
            serials = [u.get("serialNumber") for u in units if u.get("serialNumber")]
            if self.selected_serials:
                serials = [s for s in serials if s in self.selected_serials]
            details: Dict[str, Any] = {}
            for serial in serials:
                details[serial] = await self.api.get_unit(serial)
            return {"units": units, "serials": serials, "details": details}
        except Exception as err:
            raise UpdateFailed(str(err)) from err
