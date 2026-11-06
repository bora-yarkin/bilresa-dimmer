# SPDX-License-Identifier: GPL-3.0-or-later
"""Turns Fast Matter switch's events for a dimmer into what each mode's event entity reports.

The wheel's clicks arrive as ``initial_press`` of the clockwise or counter-clockwise button (the dimmer's own click count, which
comes later and is often wrong, is not used). The steps of the clicks that arrive within ``BATCH_S`` are added up and reported as
one event; the wheel press is passed on as ``press``, ``double_press`` or ``long_press`` by the rule Fast Matter switch applies.
"""

from __future__ import annotations

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later

from .const import (
    ATTR_STEPS,
    BATCH_S,
    BUTTON_COUNT,
    BUTTONS_PER_MODE,
    CLOCKWISE,
    DOMAIN,
    EVENT_CLOCKWISE,
    EVENT_COUNTER_CLOCKWISE,
    PRESS,
    PRESS_EVENT_TYPES,
)
from .dimming import Turn


def dispatch_signal(device_id: str, mode: int) -> str:
    """The signal the controller sends to the event entity of one mode of one dimmer."""
    return f"{DOMAIN}_{device_id}_{mode}"


class DimmerEvents:
    """Listens to Fast Matter switch's events and reports them to the mode entities, for every dimmer."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._turns: dict[tuple[str, int], Turn] = {}
        # The steps clicks have added up to and no event has reported yet.
        self._pending: dict[tuple[str, int], int] = {}
        self._cancel_flush: CALLBACK_TYPE | None = None

    @callback
    def handle(self, event: Event) -> None:
        data = event.data
        device_id = data.get("device_id")
        endpoint = data.get("endpoint_id")
        if not isinstance(device_id, str) or not isinstance(endpoint, int) or isinstance(endpoint, bool):
            return
        if not 1 <= endpoint <= BUTTON_COUNT:
            return
        mode, button = divmod(endpoint - 1, BUTTONS_PER_MODE)
        key = (device_id, mode + 1)
        if button == PRESS:
            if data.get("fast_event_type") in PRESS_EVENT_TYPES:
                async_dispatcher_send(self._hass, dispatch_signal(*key), data["fast_event_type"], {})
        elif data.get("event_type") == "initial_press":
            turn = self._turns.setdefault(key, Turn(self._hass.loop.time))
            self._pending[key] = self._pending.get(key, 0) + turn.click(1 if button == CLOCKWISE else -1)
            if self._cancel_flush is None:
                self._cancel_flush = async_call_later(self._hass, BATCH_S, self._flush)

    @callback
    def _flush(self, _now) -> None:
        self._cancel_flush = None
        pending, self._pending = self._pending, {}
        for key, steps in pending.items():
            if steps:
                event_type = EVENT_CLOCKWISE if steps > 0 else EVENT_COUNTER_CLOCKWISE
                async_dispatcher_send(self._hass, dispatch_signal(*key), event_type, {ATTR_STEPS: steps})

    @callback
    def stop(self) -> None:
        if self._cancel_flush is not None:
            self._cancel_flush()
            self._cancel_flush = None
