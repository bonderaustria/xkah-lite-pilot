from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util.dt import utcnow

from .const import (
    CONF_NOTIFY_MESSAGE,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TITLE,
    CONF_POWER_SENSOR,
    CONF_SWITCH_ENTITY,
    DEFAULT_COOLDOWN_TIMEOUT,
    DEFAULT_OFF_THRESHOLD,
    DEFAULT_PREHEAT_DURATION,
    DEFAULT_READY_TIMEOUT,
    DEFAULT_START_DURATION,
    DEFAULT_START_THRESHOLD,
    DOMAIN,
    MAX_SESSIONS,
    MIN_SESSION_DURATION,
    MIN_SESSIONS_FOR_LEARNING,
    STATE_COOLDOWN,
    STATE_OFF,
    STATE_PREHEATING,
    STATE_READY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


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
        self._current_readings: list[tuple[float, float]] = []

        self._sessions: list[dict[str, Any]] = []
        self._learned_duration: int = DEFAULT_PREHEAT_DURATION
        self._start_threshold: float = DEFAULT_START_THRESHOLD

        self._unsub: callback | None = None
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._notification_sent: bool = False

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
        return min(99, int(elapsed / self._learned_duration * 100))

    @property
    def remaining_seconds(self) -> int:
        if self._state != STATE_PREHEATING or not self._session_start:
            return 0
        elapsed = (utcnow() - self._session_start).total_seconds()
        return max(0, int(self._learned_duration - elapsed))

    @property
    def learned_duration(self) -> int:
        return self._learned_duration

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def is_running(self) -> bool:
        return self._state in (STATE_PREHEATING, STATE_READY)

    @property
    def current_session_elapsed(self) -> int:
        if not self._session_start:
            return 0
        return int((utcnow() - self._session_start).total_seconds())

    @property
    def power_sensor_entity(self) -> str:
        return self._power_sensor

    @property
    def switch_entity(self) -> str:
        return self._switch_entity

    async def async_start(self) -> None:
        data = await self._store.async_load()
        if data:
            self._sessions = data.get("sessions", [])
            self._learned_duration = data.get(
                "learned_duration", DEFAULT_PREHEAT_DURATION
            )
            self._start_threshold = data.get(
                "start_threshold", DEFAULT_START_THRESHOLD
            )
        self._unsub = async_track_state_change_event(
            self.hass, self._power_sensor, self._async_handle_power_update
        )
        _LOGGER.info(
            "XKah engine started for %s (learned_duration=%s, sessions=%d)",
            self.entry.title,
            self._learned_duration,
            len(self._sessions),
        )

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "sessions": self._sessions,
                "learned_duration": self._learned_duration,
                "start_threshold": self._start_threshold,
            }
        )

    @callback
    def _async_handle_power_update(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        raw = new_state.state
        if raw in ("unavailable", "unknown", None):
            return
        try:
            power = float(raw)
        except (ValueError, TypeError):
            return
        self._current_power = power
        self._process_power(power, utcnow())

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
                "State: %s → %s (power=%.1fW)", prev_state, self._state, power
            )

    def _handle_off(self, power: float, now: datetime) -> None:
        if power > self._start_threshold:
            if self._start_candidate is None:
                self._start_candidate = now
            elif (now - self._start_candidate).total_seconds() >= DEFAULT_START_DURATION:
                self._transition_to(STATE_PREHEATING, now)
        else:
            self._start_candidate = None

    def _handle_preheating(self, power: float, now: datetime) -> None:
        ts = now.timestamp()
        self._current_readings.append((ts, power))

        if power < DEFAULT_OFF_THRESHOLD:
            self._transition_to(STATE_READY, now)
            return

        if self._learned_duration and self._session_start:
            elapsed = (now - self._session_start).total_seconds()
            if elapsed >= self._learned_duration and not self._notification_sent:
                self._notification_sent = True
                self._transition_to(STATE_READY, now)
                self.hass.async_create_task(self._async_send_notification())

    def _handle_ready(self, power: float, now: datetime) -> None:
        if self._ready_since is None:
            self._ready_since = now

        if power > self._start_threshold:
            # Heater turned back on during ready phase
            self._ready_since = None
            self._transition_to(STATE_PREHEATING, now)
            return

        if power < DEFAULT_OFF_THRESHOLD:
            self._transition_to(STATE_COOLDOWN, now)
            return

        if (now - self._ready_since).total_seconds() >= DEFAULT_READY_TIMEOUT:
            self._transition_to(STATE_COOLDOWN, now)

    def _handle_cooldown(self, power: float, now: datetime) -> None:
        if power > self._start_threshold:
            self._transition_to(STATE_PREHEATING, now)
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
            self._current_readings = []
            self._notification_sent = False
            self._ready_since = None
            self._session_end = None

        elif new_state == STATE_READY:
            self._ready_since = now
            if self._session_start and self._current_readings:
                elapsed = (now - self._session_start).total_seconds()
                if elapsed >= MIN_SESSION_DURATION:
                    self.hass.async_create_task(self._async_complete_session(now))

        elif new_state == STATE_COOLDOWN:
            self._session_end = now

        elif new_state == STATE_OFF:
            self._session_start = None
            self._current_readings = []
            self._start_candidate = None
            self._ready_since = None
            self._session_end = None
            self._notification_sent = False

        async_dispatcher_send(
            self.hass, f"{DOMAIN}_{self.entry.entry_id}_update"
        )

    async def _async_complete_session(self, now: datetime) -> None:
        if not self._session_start or not self._current_readings:
            return

        duration = (now - self._session_start).total_seconds()
        powers = [p for _, p in self._current_readings]

        session = {
            "timestamp": now.isoformat(),
            "duration": round(duration),
            "readings_count": len(powers),
            "avg_power": round(sum(powers) / len(powers), 1) if powers else 0,
            "max_power": round(max(powers), 1) if powers else 0,
            "min_power": round(min(powers), 1) if powers else 0,
        }
        self._sessions.append(session)
        if len(self._sessions) > MAX_SESSIONS:
            self._sessions = self._sessions[-MAX_SESSIONS:]

        self._learned_duration = self._calculate_learned_duration()
        self._auto_adjust_threshold(powers)

        _LOGGER.info(
            "Session recorded: %ds, avg=%.1fW, learned_duration=%s, total=%d",
            session["duration"],
            session["avg_power"],
            self._learned_duration,
            len(self._sessions),
        )
        await self._async_save()

    def _calculate_learned_duration(self) -> int:
        if len(self._sessions) < MIN_SESSIONS_FOR_LEARNING:
            return DEFAULT_PREHEAT_DURATION
        total_weight = 0.0
        weighted_sum = 0.0
        n = len(self._sessions)
        for i, session in enumerate(self._sessions):
            weight = 0.9 ** (n - 1 - i)
            weighted_sum += session["duration"] * weight
            total_weight += weight
        return int(weighted_sum / total_weight)

    def _auto_adjust_threshold(self, powers: list[float]) -> None:
        if not powers:
            return
        operating_min = min(powers)
        candidate = operating_min * 0.5
        floor = DEFAULT_OFF_THRESHOLD + 1.0
        self._start_threshold = max(floor, min(candidate, DEFAULT_START_THRESHOLD))

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
            CONF_NOTIFY_MESSAGE, "Deine Kohle ist fertig!"
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
