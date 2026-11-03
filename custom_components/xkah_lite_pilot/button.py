from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENGINE, DOMAIN


class XKahMarkReadyButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Kohle fertig"
    _attr_icon = "mdi:check-circle"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_mark_ready"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="XKah",
            model="Lite",
        )

    async def async_press(self) -> None:
        engine = self.hass.data[DOMAIN][self._entry.entry_id][DATA_ENGINE]
        engine.mark_ready()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([XKahMarkReadyButton(entry)])
