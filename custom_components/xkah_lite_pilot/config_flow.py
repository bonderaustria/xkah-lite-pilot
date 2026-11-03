from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
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


def _get_notify_services(hass) -> list[dict[str, str]]:
    services = hass.services.async_services_for_domain("notify")
    options = [{"value": "", "label": "Keine Benachrichtigung"}]
    for service_name in sorted(services):
        full = f"notify.{service_name}"
        options.append({"value": full, "label": full})
    return options


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
            return await self.async_step_notify()
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

    async def async_step_power(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._power_sensor = user_input[CONF_POWER_SENSOR]
            return await self.async_step_notify()
        return self.async_show_form(
            step_id="power",
            data_schema=STEP_POWER_SCHEMA,
        )

    async def async_step_notify(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not self._power_sensor:
            return await self.async_step_power()

        if user_input is not None:
            notify_service = user_input.get(CONF_NOTIFY_SERVICE, "")
            return self.async_create_entry(
                title="XKah Lite",
                data={
                    CONF_SWITCH_ENTITY: self._switch_entity,
                    CONF_POWER_SENSOR: self._power_sensor,
                },
                options={
                    CONF_NOTIFY_SERVICE: notify_service,
                    CONF_NOTIFY_TITLE: user_input.get(
                        CONF_NOTIFY_TITLE, "XKah Lite"
                    ),
                    CONF_NOTIFY_MESSAGE: user_input.get(
                        CONF_NOTIFY_MESSAGE, "XKah Lite - PreHeat abgeschlossen!"
                    ),
                },
            )

        notify_options = _get_notify_services(self.hass)
        schema = vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_SERVICE, default=""): SelectSelector(
                    SelectSelectorConfig(
                        options=notify_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_TITLE, default="XKah Lite"
                ): TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_MESSAGE, default="XKah Lite - PreHeat abgeschlossen!"
                ): TextSelector(),
            }
        )
        return self.async_show_form(step_id="notify", data_schema=schema)

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
        notify_options = _get_notify_services(self.hass)
        current_service = options.get(CONF_NOTIFY_SERVICE, "")

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=current_service,
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=notify_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_TITLE,
                    default=options.get(CONF_NOTIFY_TITLE, "XKah Lite"),
                ): TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_MESSAGE,
                    default=options.get(
                        CONF_NOTIFY_MESSAGE, "XKah Lite - PreHeat abgeschlossen!"
                    ),
                ): TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
