# SPDX-License-Identifier: GPL-3.0-or-later
"""Setup flow: pick the dimmer, then the lights of each of its three modes."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import BUTTON_COUNT, CONF_DEVICE_ID, DOMAIN, FAST_MATTER_SWITCH_DOMAIN, MATTER_DOMAIN, MODES, conf_lights

_LIGHTS = selector.EntitySelector(selector.EntitySelectorConfig(domain="light", multiple=True))


def _lights_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(conf_lights(1)): _LIGHTS,
            **{vol.Optional(conf_lights(mode)): _LIGHTS for mode in MODES[1:]},
        }
    )


def _lights_options(user_input: dict[str, Any]) -> dict[str, list[str]]:
    return {conf_lights(mode): user_input.get(conf_lights(mode), []) for mode in MODES}


def _is_dimmer(hass, device_id: str) -> bool:
    """The dimmer shows up in Matter as one device with nine buttons (three for each mode)."""
    entries = er.async_entries_for_device(er.async_get(hass), device_id)
    return sum(1 for e in entries if e.platform == MATTER_DOMAIN and e.domain == "event") == BUTTON_COUNT


class BilresaDimmerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._device_id = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BilresaDimmerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self.hass.config_entries.async_loaded_entries(FAST_MATTER_SWITCH_DOMAIN):
            return self.async_abort(reason="no_fast_matter_switch")
        errors: dict[str, str] = {}
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            if _is_dimmer(self.hass, device_id):
                self._device_id = device_id
                return await self.async_step_lights()
            errors["base"] = "not_a_dimmer"
        schema = vol.Schema(
            {vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(selector.DeviceSelectorConfig(integration=MATTER_DOMAIN))}
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_lights(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            device = dr.async_get(self.hass).async_get(self._device_id)
            title = (device.name_by_user or device.name) if device else "BILRESA dimmer"
            return self.async_create_entry(title=title, data={CONF_DEVICE_ID: self._device_id}, options=_lights_options(user_input))
        return self.async_show_form(step_id="lights", data_schema=_lights_schema())


class BilresaDimmerOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_lights_options(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_lights_schema(), self.config_entry.options),
        )
