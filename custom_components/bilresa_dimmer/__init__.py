# SPDX-License-Identifier: GPL-3.0-or-later
"""IKEA BILRESA dimmer.

The dimmer's wheel reports each click as a press of a Matter button, and the Matter integration holds those presses back until
the multi-press window has run out, which makes dimming late and uneven. Fast Matter switch reports every press the moment the
dimmer sends it; this integration listens to those events (``fast_matter_switch_event``) and
  - dims or brightens the lights of the current mode by a step for every wheel click, with a short fade, in larger steps the
    longer a turn goes on (dimming.py), and applies the clicks the dimmer's radio sends together as one change;
  - toggles the lights of the current mode when the wheel is pressed.

The dimmer has three modes and sends nothing when the mode changes: each mode simply uses its own three Matter buttons
(counter-clockwise, clockwise, press), so the mode is known from the button that fired. Each mode has its own lights.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_call_later

from .const import (
    BATCH_S,
    BUTTON_COUNT,
    BUTTONS_PER_MODE,
    CLOCKWISE,
    CONF_DEVICE_ID,
    FAST_EVENT,
    FAST_MATTER_SWITCH_DOMAIN,
    MIN_BRIGHTNESS_PCT,
    MODES,
    PRESS,
    TRANSITION_S,
    TURN_GAP_S,
    conf_lights,
)
from .dimming import Turn

_LOGGER = logging.getLogger(__name__)


def _brightness_percent(brightness: int) -> int:
    return max(MIN_BRIGHTNESS_PCT, round(brightness * 100 / 255))


class DimmerController:
    """Turns one dimmer's Fast Matter switch events into light calls."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device_id: str, lights: dict[int, list[str]]) -> None:
        self._hass = hass
        self._entry = entry
        self._device_id = device_id
        self._lights = lights
        self._turns = {mode: Turn(hass.loop.time) for mode in MODES}
        # The percentage clicks have asked for and no light call has carried yet, for each mode.
        self._pending: dict[int, int] = {}
        self._cancel_flush: CALLBACK_TYPE | None = None
        # What the last call asked each light to be (percent, time). While a fade is running the light's own state still
        # shows the old brightness, so the next click builds on this instead.
        self._targets: dict[str, tuple[int, float]] = {}

    @callback
    def handle(self, event: Event) -> None:
        data = event.data
        if data.get("device_id") != self._device_id:
            return
        endpoint = data.get("endpoint_id")
        if not isinstance(endpoint, int) or isinstance(endpoint, bool) or not 1 <= endpoint <= BUTTON_COUNT:
            return
        mode, button = divmod(endpoint - 1, BUTTONS_PER_MODE)
        mode += 1
        if not self._lights.get(mode):
            return
        if button == PRESS:
            if data.get("fast_event_type") == "press":
                self._run(self._toggle(mode), f"toggle mode {mode}")
        elif data.get("event_type") == "initial_press":
            percent = self._turns[mode].click(1 if button == CLOCKWISE else -1)
            self._pending[mode] = self._pending.get(mode, 0) + percent
            if self._cancel_flush is None:
                self._cancel_flush = async_call_later(self._hass, BATCH_S, self._flush)

    @callback
    def stop(self) -> None:
        if self._cancel_flush is not None:
            self._cancel_flush()
            self._cancel_flush = None

    def _run(self, coro, name: str) -> None:
        self._entry.async_create_background_task(self._hass, coro, f"{self._entry.title}: {name}")

    async def _flush(self, _now) -> None:
        self._cancel_flush = None
        pending, self._pending = self._pending, {}
        for mode, percent in pending.items():
            if percent:
                await self._dim(self._lights[mode], percent)

    async def _dim(self, entity_ids: Iterable[str], percent: int) -> None:
        now = self._hass.loop.time()
        for entity_id in entity_ids:
            state = self._hass.states.get(entity_id)
            if state is None:
                continue
            if state.state == "on":
                brightness = state.attributes.get("brightness")
                if brightness is None:  # a light that cannot be dimmed
                    continue
                target, at = self._targets.get(entity_id, (None, 0.0))
                base = target if target is not None and now - at <= TURN_GAP_S else _brightness_percent(brightness)
            elif state.state == "off" and percent > 0:
                base = 0
            else:  # off and dimming further, or unavailable
                continue
            new = min(100, max(MIN_BRIGHTNESS_PCT, base + percent))
            self._targets[entity_id] = (new, now)
            await self._hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": entity_id, "brightness_pct": new, "transition": TRANSITION_S},
                blocking=False,
            )

    async def _toggle(self, mode: int) -> None:
        for entity_id in self._lights[mode]:
            self._targets.pop(entity_id, None)
        await self._hass.services.async_call("light", "toggle", {"entity_id": self._lights[mode]}, blocking=False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not hass.config_entries.async_loaded_entries(FAST_MATTER_SWITCH_DOMAIN):
        raise ConfigEntryNotReady("Fast Matter switch is not set up yet")
    lights = {mode: list(entry.options.get(conf_lights(mode), [])) for mode in MODES}
    controller = DimmerController(hass, entry, entry.data[CONF_DEVICE_ID], lights)
    entry.async_on_unload(hass.bus.async_listen(FAST_EVENT, controller.handle))
    entry.async_on_unload(controller.stop)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
