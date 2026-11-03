from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util.dt import utcnow

from .const import (
    CONF_NOTIFY_MESSAGE,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TITLE,
    CONF_POWER_SENSOR,
    CONF_SWITCH_ENTITY,
    DEFAULT_COOLDOWN_TIMEOUT,
    DEFAULT_LOW_POWER_GRACE,
    DEFAULT_OFF_THRESHOLD,
    DEFAULT_PREHEAT_DURATION,
    DEFAULT_SESSION_DURATION,
    DEFAULT_START_DURATION,
    DEFAULT_START_THRESHOLD,
    DOMAIN,
    STATE_COOLDOWN,
    STATE_OFF,
    STATE_PREHEATING,
    STATE_READY,
)

_LOGGER = logging.getLogger(__name__)

TICK_INTERVAL = 1


class XKahEngine:

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self._power_sensor: str = entry.data[CONF_POWER_SENSOR]
        self._switch_entity: str = entry.data[CONF_SWITCH_ENTITY]

        self._state: str = STATE_OFF
        self._current_power: float = 0.0
        self._session_start: datetime | None = None
        self._session_end: datetime | None = None
        self._ready_since: datetime | None = None
        self._start_candidate: datetime | None = None
        self._low_power_since: datetime | None = None
        self._notification_sent: bool = False
        self._unsub_power: CALLBACK_TYPE | None = None
        self._unsub_tick: CALLBACK_TYPE | None = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_power(self) -> float:
        return self._current_power

    @property
    def progress(self) -> int:
        if self._state != STATE_PREHEATING or not self._session_start:
            return 0
        elapsed = (utcnow() - self._session_start).total_seconds()
        return min(99, int(elapsed / DEFAULT_PREHEAT_DURATION * 100))

    @property
    def remaining_seconds(self) -> int:
        if self._state != STATE_PREHEATING or not self._session_start:
            return 0
        elapsed = (utcnow() - self._session_start).total_seconds()
        return max(0, int(DEFAULT_PREHEAT_DURATION - elapsed))

    @property
    def session_remaining(self) -> int:
        if self._state != STATE_READY or not self._ready_since:
            return 0
        elapsed = (utcnow() - self._ready_since).total_seconds()
        return max(0, int(DEFAULT_SESSION_DURATION - elapsed))

    @property
    def is_running(self) -> bool:
        return self._state in (STATE_PREHEATING, STATE_READY)

    @property
    def power_sensor_entity(self) -> str:
        return self._power_sensor

    @property
    def switch_entity(self) -> str:
        return self._switch_entity

    async def async_start(self) -> None:
        from datetime import timedelta

        self._unsub_power = async_track_state_change_event(
            self.hass, self._power_sensor, self._async_handle_power_update
        )
        self._unsub_tick = async_track_time_interval(
            self.hass, self._async_tick, timedelta(seconds=TICK_INTERVAL)
        )
        _LOGGER.info("XKah engine started for %s", self.entry.title)

    async def async_stop(self) -> None:
        if self._unsub_power:
            self._unsub_power()
            self._unsub_power = None
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None

    @callback
    def _async_handle_power_update(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        raw = new_state.state
        if raw in ("unavailable", "unknown", None):
            power = 0.0
        else:
            try:
                power = float(raw)
            except (ValueError, TypeError):
                return
        self._current_power = power
        self._process_power(power, utcnow())

    @callback
    def _async_tick(self, now: datetime) -> None:
        if self._state in (STATE_PREHEATING, STATE_READY):
            self._process_power(self._current_power, now)
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self.entry.entry_id}_update"
            )

    def _process_power(self, power: float, now: datetime) -> None:
        prev_state = self._state

        if self._state == STATE_OFF:
            self._handle_off(power, now)
        elif self._state == STATE_PREHEATING:
            self._handle_preheating(power, now)
        elif self._state == STATE_READY:
            self._handle_ready(power, now)
        elif self._state == STATE_COOLDOWN:
            self._handle_cooldown(power, now)

        if self._state != prev_state:
            _LOGGER.debug(
                "State: %s -> %s (power=%.1fW)", prev_state, self._state, power
            )

    def _handle_off(self, power: float, now: datetime) -> None:
        if power > DEFAULT_START_THRESHOLD:
            if self._start_candidate is None:
                self._start_candidate = now
            elif (now - self._start_candidate).total_seconds() >= DEFAULT_START_DURATION:
                self._transition_to(STATE_PREHEATING, now)
        else:
            self._start_candidate = None

    def _handle_preheating(self, power: float, now: datetime) -> None:
        if power < DEFAULT_OFF_THRESHOLD:
            if self._low_power_since is None:
                self._low_power_since = now
            elif (now - self._low_power_since).total_seconds() >= DEFAULT_LOW_POWER_GRACE:
                self._low_power_since = None
                self._transition_to(STATE_READY, now)
            return
        else:
            self._low_power_since = None

        if self._session_start:
            elapsed = (now - self._session_start).total_seconds()
            if elapsed >= DEFAULT_PREHEAT_DURATION and not self._notification_sent:
                self._notification_sent = True
                self._transition_to(STATE_READY, now)
                self.hass.async_create_task(self._async_send_notification())

    def _handle_ready(self, power: float, now: datetime) -> None:
        if self._ready_since is None:
            self._ready_since = now

        if power < DEFAULT_OFF_THRESHOLD:
            if self._low_power_since is None:
                self._low_power_since = now
            elif (now - self._low_power_since).total_seconds() >= DEFAULT_LOW_POWER_GRACE:
                self._low_power_since = None
                self._transition_to(STATE_COOLDOWN, now)
        else:
            self._low_power_since = None

    def _handle_cooldown(self, power: float, now: datetime) -> None:
        if power >= DEFAULT_OFF_THRESHOLD:
            self._session_end = now
            return

        if self._session_end:
            since_end = (now - self._session_end).total_seconds()
            if since_end >= DEFAULT_COOLDOWN_TIMEOUT:
                self._transition_to(STATE_OFF, now)

    def _transition_to(self, new_state: str, now: datetime) -> None:
        old_state = self._state
        self._state = new_state

        if new_state == STATE_PREHEATING and old_state == STATE_OFF:
            self._session_start = now
            self._notification_sent = False
            self._ready_since = None
            self._session_end = None
            self._low_power_since = None

        elif new_state == STATE_READY:
            self._ready_since = now

        elif new_state == STATE_COOLDOWN:
            self._session_end = now

        elif new_state == STATE_OFF:
            self._session_start = None
            self._start_candidate = None
            self._ready_since = None
            self._session_end = None
            self._notification_sent = False
            self._low_power_since = None

        async_dispatcher_send(
            self.hass, f"{DOMAIN}_{self.entry.entry_id}_update"
        )

    async def _async_send_notification(self) -> None:
        service = self.entry.options.get(CONF_NOTIFY_SERVICE)
        if not service:
            return
        parts = service.split(".", 1)
        if len(parts) != 2:
            _LOGGER.warning("Invalid notify service format: %s", service)
            return
        domain, service_name = parts
        title = self.entry.options.get(CONF_NOTIFY_TITLE, "XKah Lite")
        message = self.entry.options.get(
            CONF_NOTIFY_MESSAGE, "XKah Lite - PreHeat abgeschlossen!"
        )
        try:
            await self.hass.services.async_call(
                domain,
                service_name,
                {"title": title, "message": message},
                blocking=False,
            )
        except Exception:
            _LOGGER.exception("Failed to send notification")

    def mark_ready(self) -> None:
        if self._state != STATE_PREHEATING:
            return
        now = utcnow()
        self._transition_to(STATE_READY, now)
        self.hass.async_create_task(self._async_send_notification())
