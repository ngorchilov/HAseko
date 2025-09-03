from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AsekoCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AsekoCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    serials = data.get("serials", []) or []

    entities: list[BinarySensorEntity] = []

    for serial in serials:
        units_list = data.get("units") or []
        unit_meta = next((u for u in units_list if u.get("serialNumber") == serial), {})
        dev_name = unit_meta.get("name") or f"Unit {serial}"

        # Online comes from the unit list (not statusValues)
        entities.append(AsekoBinary(coordinator, serial, "online", f"{dev_name} Online", source="unit"))

        # The rest come from statusValues
        for key, label in {
            "filtrationRunning": "Filtration",
            "waterFlowToProbes": "Water Flow to Probes",
            "electrolyzerRunning": "Electrolyzer",
            "heatingRunning": "Heating",
            "solarRunning": "Solar",
            "waterFillingRunning": "Water Filling",
        }.items():
            entities.append(AsekoBinary(coordinator, serial, key, f"{dev_name} {label}", source="values"))

    async_add_entities(entities)


class AsekoBinary(CoordinatorEntity[AsekoCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: AsekoCoordinator, serial: str, key: str, name: str, source: str = "values") -> None:
        """
        source: "values" -> from statusValues[key]
                "unit"   -> from unit meta (e.g., online)
        """
        super().__init__(coordinator)
        self._serial = serial
        self._key = key
        self._source = source
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_name = name

    @property
    def is_on(self):
        try:
            if self._source == "unit":
                unit_meta = next((u for u in (self.coordinator.data.get("units") or []) if u.get("serialNumber") == self._serial), {})
                v = unit_meta.get(self._key)
            else:
                detail = (self.coordinator.data.get("details") or {}).get(self._serial, {})
                values = detail.get("statusValues") or {}
                v = values.get(self._key)
            return bool(v) if v is not None else None
        except Exception:
            return None

    @property
    def device_class(self):
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