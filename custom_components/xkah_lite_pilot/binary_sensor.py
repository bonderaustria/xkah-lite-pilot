from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENGINE, DOMAIN


class XKahRunningSensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_name = "Läuft"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_running"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="XKah",
            model="Lite",
        )

    @property
    def is_on(self) -> bool:
        engine = self.hass.data[DOMAIN][self._entry.entry_id][DATA_ENGINE]
        return engine.is_running

    async def async_added_to_hass(self) -> None:
        signal = f"{DOMAIN}_{self._entry.entry_id}_update"
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([XKahRunningSensor(entry)])
