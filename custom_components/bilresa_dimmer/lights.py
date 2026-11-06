# SPDX-License-Identifier: GPL-3.0-or-later
"""The ``bilresa_dimmer.adjust_light`` action: moves a light's brightness or colour temperature by a number of steps."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.core import HomeAssistant

from .const import BRIGHTNESS, COLOR_TEMP, MIN_BRIGHTNESS_PCT, TURN_GAP_S


class LightAdjuster:
    """Moves lights by steps, building on what it last asked for while a light is still fading to it.

    A light's own state shows the old value until its fade ends, so a click that follows closely would otherwise start from
    the old value and the lights would lag behind the wheel. What was asked for is trusted for ``TURN_GAP_S``, then the light's
    own state is read again (someone may have changed it meanwhile).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        # (entity id, attribute) -> (the value last asked for, when). Brightness is a percentage, colour temperature kelvin.
        self._asked: dict[tuple[str, str], tuple[float, float]] = {}

    async def adjust(self, entity_ids: Iterable[str], attribute: str, steps: float, percent: float, transition: float) -> None:
        """Move each light by ``steps`` steps of ``percent`` percent of its range; positive is brighter / cooler."""
        for entity_id in entity_ids:
            state = self._hass.states.get(entity_id)
            if state is None or not steps:
                continue
            data = (
                self._brightness(entity_id, state, steps * percent)
                if attribute == BRIGHTNESS
                else self._color_temp(entity_id, state, steps * percent)
            )
            if data is not None:
                await self._hass.services.async_call(
                    "light", "turn_on", {"entity_id": entity_id, "transition": transition, **data}, blocking=False
                )

    def _base(self, entity_id: str, attribute: str, current: float) -> float:
        asked, at = self._asked.get((entity_id, attribute), (None, 0.0))
        return asked if asked is not None and self._hass.loop.time() - at <= TURN_GAP_S else current

    def _remember(self, entity_id: str, attribute: str, value: float) -> None:
        self._asked[(entity_id, attribute)] = (value, self._hass.loop.time())

    def _brightness(self, entity_id: str, state, change: float) -> dict | None:
        if state.state == "on":
            brightness = state.attributes.get("brightness")
            if brightness is None:  # a light that cannot be dimmed
                return None
            base = self._base(entity_id, BRIGHTNESS, brightness * 100 / 255)
        elif state.state == "off" and change > 0:
            base = 0.0
        else:  # off and dimming further, or unavailable
            return None
        new = min(100, max(MIN_BRIGHTNESS_PCT, round(base + change)))
        self._remember(entity_id, BRIGHTNESS, new)
        return {"brightness_pct": new}

    def _color_temp(self, entity_id: str, state, change: float) -> dict | None:
        kelvin = state.attributes.get("color_temp_kelvin")
        low = state.attributes.get("min_color_temp_kelvin")
        high = state.attributes.get("max_color_temp_kelvin")
        # Off, unavailable, or not in colour temperature mode (a colour is showing): leave it alone.
        if state.state != "on" or kelvin is None or low is None or high is None or high <= low:
            return None
        base = self._base(entity_id, COLOR_TEMP, kelvin)
        new = min(high, max(low, round(base + change / 100 * (high - low))))
        self._remember(entity_id, COLOR_TEMP, new)
        return {"color_temp_kelvin": new}
