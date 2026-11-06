# SPDX-License-Identifier: GPL-3.0-or-later
"""IKEA BILRESA dimmer.

The dimmer's wheel reports each click as a press of a Matter button, and the Matter integration holds those presses back until
the multi-press window has run out, which makes dimming late and uneven. Fast Matter switch reports every press the moment the
dimmer sends it. This integration turns those events into one event entity for each of the dimmer's three modes (event.py,
events.py) and adds the ``bilresa_dimmer.adjust_light`` action (lights.py). What a mode controls, and by how much, is decided in
the user's automations: nothing is set up in the integration.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ATTRIBUTE,
    ATTR_PERCENT,
    ATTR_STEPS,
    ATTR_TRANSITION,
    BRIGHTNESS,
    COLOR_TEMP,
    DEFAULT_PERCENT,
    DEFAULT_TRANSITION_S,
    DOMAIN,
    FAST_EVENT,
    FAST_MATTER_SWITCH_DOMAIN,
    SERVICE_ADJUST_LIGHT,
)
from .events import DimmerEvents
from .lights import LightAdjuster

PLATFORMS = [Platform.EVENT]

ADJUST_LIGHT_SCHEMA = vol.Schema(
    {
        **cv.TARGET_SERVICE_FIELDS,
        vol.Required(ATTR_ATTRIBUTE): vol.In([BRIGHTNESS, COLOR_TEMP]),
        vol.Required(ATTR_STEPS): vol.All(vol.Coerce(int), vol.Range(min=-100, max=100)),
        vol.Optional(ATTR_PERCENT, default=DEFAULT_PERCENT): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=100)),
        vol.Optional(ATTR_TRANSITION, default=DEFAULT_TRANSITION_S): vol.All(vol.Coerce(float), vol.Range(min=0, max=60)),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    adjuster = LightAdjuster(hass)

    async def adjust_light(call: ServiceCall) -> None:
        # A device or area target also names its other entities; only the lights are moved.
        lights = sorted(e for e in await service.async_extract_entity_ids(call) if e.startswith("light."))
        await adjuster.adjust(lights, call.data[ATTR_ATTRIBUTE], call.data[ATTR_STEPS], call.data[ATTR_PERCENT], call.data[ATTR_TRANSITION])

    hass.services.async_register(DOMAIN, SERVICE_ADJUST_LIGHT, adjust_light, schema=ADJUST_LIGHT_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not hass.config_entries.async_loaded_entries(FAST_MATTER_SWITCH_DOMAIN):
        raise ConfigEntryNotReady("Fast Matter switch is not set up yet")
    events = DimmerEvents(hass)
    entry.async_on_unload(events.stop)
    entry.async_on_unload(hass.bus.async_listen(FAST_EVENT, events.handle))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
