from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
)

from .const import (
    CONF_NOTIFY_MESSAGE,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TITLE,
    CONF_POWER_SENSOR,
    CONF_SWITCH_ENTITY,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SWITCH_ENTITY): EntitySelector(
            EntitySelectorConfig(domain="switch")
        ),
    }
)

STEP_POWER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POWER_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="power")
        ),
    }
)


class XKahLitePilotConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._switch_entity: str | None = None
        self._power_sensor: str | None = None

    @staticmethod
    def async_get_options_flow(config_entry):
        return XKahLitePilotOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._switch_entity = user_input[CONF_SWITCH_ENTITY]
            power = self._find_power_sensor(self._switch_entity)
            if power:
                self._power_sensor = power
                return self.async_create_entry(
                    title="XKah Lite",
                    data={
                        CONF_SWITCH_ENTITY: self._switch_entity,
                        CONF_POWER_SENSOR: self._power_sensor,
                    },
                )
            return await self.async_step_power()
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

    async def async_step_power(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._power_sensor = user_input[CONF_POWER_SENSOR]
            return self.async_create_entry(
                title="XKah Lite",
                data={
                    CONF_SWITCH_ENTITY: self._switch_entity,
                    CONF_POWER_SENSOR: self._power_sensor,
                },
            )
        return self.async_show_form(
            step_id="power",
            data_schema=STEP_POWER_SCHEMA,
            description_placeholders={
                "switch_entity": self._switch_entity or "",
            },
        )

    def _find_power_sensor(self, switch_entity_id: str) -> str | None:
        ent_reg = er.async_get(self.hass)
        switch_entry = ent_reg.async_get(switch_entity_id)
        if not switch_entry or not switch_entry.device_id:
            return None
        for entry in ent_reg.entities.get_entries_for_device_id(
            switch_entry.device_id
        ):
            if (
                entry.domain == "sensor"
                and entry.original_device_class == "power"
                and not entry.disabled_by
            ):
                return entry.entity_id
        return None


class XKahLitePilotOptionsFlow(OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=options.get(CONF_NOTIFY_SERVICE, ""),
                ): TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_TITLE,
                    default=options.get(CONF_NOTIFY_TITLE, "XKah Lite"),
                ): TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_MESSAGE,
                    default=options.get(
                        CONF_NOTIFY_MESSAGE, "Deine Kohle ist fertig!"
                    ),
                ): TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
