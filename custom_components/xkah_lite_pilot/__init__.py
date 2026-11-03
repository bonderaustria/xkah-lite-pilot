import logging
import os

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant

from .const import DATA_ENGINE, DOMAIN, PLATFORMS
from .engine import XKahEngine

_LOGGER = logging.getLogger(__name__)

CARD_JS = "xkah-lite-pilot-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"
RESOURCE_REGISTERED = f"{DOMAIN}_resource_registered"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            url_path=CARD_URL,
            path=os.path.join(os.path.dirname(__file__), CARD_JS),
            cache_headers=False,
        )
    ])
    return True


async def _async_register_card_resource(hass: HomeAssistant) -> None:
    if hass.data.get(RESOURCE_REGISTERED):
        return
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            _LOGGER.debug("Lovelace not available, skipping resource registration")
            return
        resources = lovelace.get("resources")
        if resources is None:
            _LOGGER.debug("Lovelace resources not available (YAML mode?)")
            return
        for item in resources.async_items():
            if CARD_URL in item.get("url", ""):
                hass.data[RESOURCE_REGISTERED] = True
                return
        await resources.async_create_item({"url": CARD_URL, "res_type": "module"})
        hass.data[RESOURCE_REGISTERED] = True
        _LOGGER.info("Registered Lovelace resource: %s", CARD_URL)
    except Exception:
        _LOGGER.warning("Could not auto-register Lovelace resource", exc_info=True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    engine = XKahEngine(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = {DATA_ENGINE: engine}

    await engine.async_start()
    entry.async_on_unload(engine.async_stop)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    if hass.is_running:
        await _async_register_card_resource(hass)
    else:
        async def _on_started(_event: Event) -> None:
            await _async_register_card_resource(hass)

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
