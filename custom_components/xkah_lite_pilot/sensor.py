from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENGINE, DOMAIN


class XKahSensorBase(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, suffix: str, name: str) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_name = name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="XKah",
            model="Lite",
        )

    @property
    def _engine(self):
        return self.hass.data[DOMAIN][self._entry.entry_id][DATA_ENGINE]

    async def async_added_to_hass(self) -> None:
        signal = f"{DOMAIN}_{self._entry.entry_id}_update"
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class XKahStatusSensor(XKahSensorBase):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off", "preheating", "ready", "cooldown"]
    _attr_icon = "mdi:hookah"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "status", "Status")

    @property
    def native_value(self) -> str:
        return self._engine.state


class XKahProgressSensor(XKahSensorBase):
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:progress-clock"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "progress", "Fortschritt")

    @property
    def native_value(self) -> float:
        return self._engine.progress


class XKahRemainingSensor(XKahSensorBase):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-outline"
    _attr_suggested_display_precision = 0

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "remaining", "Verbleibend")

    @property
    def native_value(self) -> int:
        return self._engine.remaining_seconds


class XKahSessionRemainingSensor(XKahSensorBase):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-sand"
    _attr_suggested_display_precision = 0

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "session_remaining", "Session Verbleibend")

    @property
    def native_value(self) -> int:
        return self._engine.session_remaining


class XKahCurrentPowerSensor(XKahSensorBase):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "current_power", "Aktuelle Leistung")

    @property
    def native_value(self) -> float:
        return self._engine.current_power


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([
        XKahStatusSensor(entry),
        XKahProgressSensor(entry),
        XKahRemainingSensor(entry),
        XKahSessionRemainingSensor(entry),
        XKahCurrentPowerSensor(entry),
    ])
