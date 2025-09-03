from __future__ import annotations

from typing import Any, Dict, Optional, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AsekoCoordinator


def _device_name(unit: Dict[str, Any]) -> str:
    return unit.get("name") or f"Unit {unit.get('serialNumber')}"


def _probe_type(values: Dict[str, Any]) -> Optional[str]:
    redox_present = values.get("redox") is not None
    cl_present = values.get("clFree") is not None
    if redox_present and not cl_present:
        return "Redox"
    if cl_present and not redox_present:
        return "Free chlorine"
    if redox_present and cl_present:
        return "Redox & Free chlorine"
    return None


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AsekoCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    serials = data.get("serials", [])

    entities: list[SensorEntity] = []

    for serial in serials:
        unit_meta = next((u for u in data.get("units", []) if u.get("serialNumber") == serial), {})
        detail = data.get("details", {}).get(serial, {})
        values = detail.get("statusValues") or {}

        dev_name = _device_name(unit_meta)

        # Text sensor: probe
        entities.append(AsekoTextSensor(coordinator, serial, "probe", f"{dev_name} Disinfection Probe",
                                        lambda: _probe_type(values)))

        # Status message (latest)
        def _latest_status() -> Optional[str]:
            msgs = detail.get("statusMessages") or []
            if not msgs:
                return None
            m = msgs[0]
            txt = m.get("message") or m.get("type")
            sev = m.get("severity")
            if sev and txt:
                return f"[{sev}] {txt}"
            return txt

        entities.append(AsekoTextSensor(coordinator, serial, "status", f"{dev_name} Status", _latest_status))

        def gv(key: str) -> Callable[[], Any]:
            return lambda: (detail.get("statusValues") or {}).get(key)

        probe = _probe_type(values) or ""

        # Numeric sensors
        entities += [
            AsekoNumberSensor(coordinator, serial, "water_temp", f"{dev_name} Water Temperature", "°C", gv("waterTemperature"), device_class="temperature", precision=1),
            AsekoNumberSensor(coordinator, serial, "water_temp_target", f"{dev_name} Water Temperature Target", "°C", gv("waterTemperatureRequired"), precision=0),
            AsekoNumberSensor(coordinator, serial, "ph", f"{dev_name} pH", None, gv("ph"), precision=2),
            AsekoNumberSensor(coordinator, serial, "ph_target", f"{dev_name} pH Target", None, gv("phRequired"), precision=2),
            AsekoNumberSensor(coordinator, serial, "salinity", f"{dev_name} Salinity", "kg/m³", gv("salinity"), precision=1),
            AsekoNumberSensor(coordinator, serial, "filter_flow", f"{dev_name} Filter Flow", "m³/h", gv("filterFlowSpeed"), precision=1),
            AsekoNumberSensor(coordinator, serial, "filter_pressure", f"{dev_name} Filter Pressure", "bar", gv("filterPressure"), device_class="pressure", precision=2),
            AsekoNumberSensor(coordinator, serial, "electrolyzer_power", f"{dev_name} Electrolyzer Production", "g/h", gv("electrodePower"), precision=0),
            AsekoNumberSensor(coordinator, serial, "water_level", f"{dev_name} Water Level", "cm", gv("waterLevel"), device_class="distance", precision=0),
        ]

        if "Redox" in probe:
            entities += [
                AsekoNumberSensor(coordinator, serial, "redox", f"{dev_name} Redox", "mV", gv("redox"), precision=0),
                AsekoNumberSensor(coordinator, serial, "redox_target", f"{dev_name} Redox Target", "mV", gv("redoxRequired"), precision=0),
            ]
        elif "Free chlorine" in probe:
            entities += [
                AsekoNumberSensor(coordinator, serial, "cl_free", f"{dev_name} Free Chlorine", "mg/L", gv("clFree"), precision=2),
                # Target stays a text sensor since its unit can vary per device
            ]

        # Enums/text
        for key, name in {
            "mode": "Mode",
            "filtrationSpeed": "Filtration Speed",
            "poolFlow": "Pool Flow",
            "electrolyzerDirection": "Electrolyzer Direction",
            "waterLevelState": "Water Level State",
            "upcomingFiltrationPeriod": "Upcoming Filtration Period",
        }.items():
            entities.append(AsekoTextSensor(coordinator, serial, key, f"{dev_name} {name}", gv(key)))

    async_add_entities(entities)


class AsekoBaseEntity(CoordinatorEntity[AsekoCoordinator]):
    def __init__(self, coordinator: AsekoCoordinator, serial: str, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_name = name

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


class AsekoNumberSensor(AsekoBaseEntity, SensorEntity):
    def __init__(self, coordinator, serial, key, name, unit, getter, device_class: str | None = None, precision: int | None = None) -> None:
        super().__init__(coordinator, serial, key, name)
        self._unit = unit
        self._getter = getter
        self._device_class = device_class
        self._precision = precision

    @property
    def native_value(self):
        try:
            val = self._getter()
            if val is None:
                return None
            if isinstance(val, (int, float)) and self._precision is not None:
                return round(val, self._precision)
            return val
        except Exception:
            return None

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class

    @property
    def state_class(self):
        return "measurement"
    

class AsekoTextSensor(AsekoBaseEntity, SensorEntity):
    def __init__(self, coordinator: AsekoCoordinator, serial: str, key: str, name: str, getter) -> None:
        super().__init__(coordinator, serial, key, name)
        self._getter = getter

    @property
    def native_value(self):
        try:
            v = self._getter()
            if isinstance(v, dict):
                is_next = v.get("isNext"); is_nonstop = v.get("isNonstop"); start = v.get("start"); end = v.get("end")
                if is_nonstop and not start and not end:
                    return "nonstop" + (" (next)" if is_next else "")
                parts = []
                if start: parts.append(start)
                if end: parts.append(end)
                s = " – ".join(parts)
                if is_nonstop: s = (s + " (nonstop)").strip()
                if is_next: s = (s + " (next)").strip()
                return s or None
            return v
        except Exception:
            return None
