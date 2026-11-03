from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_SWITCH_ENTITY, DOMAIN


class XKahSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_name = "Steckdose"
    _attr_icon = "mdi:power-plug"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._switch_entity_id: str = entry.data[CONF_SWITCH_ENTITY]
        self._attr_unique_id = f"{entry.entry_id}_switch"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="XKah",
            model="Lite",
        )

    @property
    def is_on(self) -> bool | None:
        state = self.hass.states.get(self._switch_entity_id)
        if state is None:
            return None
        return state.state == STATE_ON

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.services.async_call(
            "switch",
            "turn_on",
            target={"entity_id": self._switch_entity_id},
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.services.async_call(
            "switch",
            "turn_off",
            target={"entity_id": self._switch_entity_id},
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self._switch_entity_id,
                self._source_state_changed,
            )
        )

    @callback
    def _source_state_changed(self, event: Event) -> None:
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([XKahSwitch(entry)])
