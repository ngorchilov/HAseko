from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AsekoCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AsekoCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    serials = data.get("serials", [])

    entities: list[BinarySensorEntity] = []

    for serial in serials:
        unit_meta = next((u for u in data.get("units", []) if u.get("serialNumber") == serial), {})
        detail = data.get("details", {}).get(serial, {})
        dev_name = unit_meta.get("name") or f"Unit {serial}"

        def gv(key: str):
            return lambda: (detail.get("statusValues") or {}).get(key)

        # Online (from unit list)
        online = unit_meta.get("online")
        entities.append(AsekoBinary(coordinator, serial, "online", f"{dev_name} Online", lambda: online))

        for key, label in {
            "filtrationRunning": "Filtration",
            "waterFlowToProbes": "Water Flow to Probes",
            "electrolyzerRunning": "Electrolyzer",
            "heatingRunning": "Heating",
            "solarRunning": "Solar",
            "waterFillingRunning": "Water Filling",
        }.items():
            entities.append(AsekoBinary(coordinator, serial, key, f"{dev_name} {label}", gv(key)))

    async_add_entities(entities)


class AsekoBinary(CoordinatorEntity[AsekoCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: AsekoCoordinator, serial: str, key: str, name: str, getter) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._key = key
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_name = name
        self._getter = getter

    @property
    def device_class(self):
        # Map by key
        mapping = {
            "online": "connectivity",
            "filtrationRunning": "running",
            "waterFlowToProbes": "running",
            "electrolyzerRunning": "running",
            "heatingRunning": "heat",
            "solarRunning": "running",
            "waterFillingRunning": "running",
        }
        return mapping.get(self._key)

    @property
    def is_on(self):
        try:
            v = self._getter()
            return bool(v) if v is not None else None
        except Exception:
            return None

    @property
    def device_info(self):
        unit_meta = next((u for u in (self.coordinator.data.get("units") or []) if u.get("serialNumber") == self._serial), {})
        brand = (unit_meta.get("brandName") or {}).get("primary")
        return {
            "identifiers": {("haseko", self._serial)},
            "name": unit_meta.get("name") or f"Aseko {self._serial}",
            "manufacturer": brand or "Aseko",
            "model": (unit_meta.get("brandName") or {}).get("secondary") or "",
        }
