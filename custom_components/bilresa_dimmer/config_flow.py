# SPDX-License-Identifier: GPL-3.0-or-later
"""Setup flow: a single confirmation, no settings. Every BILRESA dimmer in Matter gets its entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, FAST_MATTER_SWITCH_DOMAIN


class BilresaDimmerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if not self.hass.config_entries.async_loaded_entries(FAST_MATTER_SWITCH_DOMAIN):
            return self.async_abort(reason="no_fast_matter_switch")
        if user_input is not None:
            return self.async_create_entry(title="IKEA BILRESA dimmer", data={})
        return self.async_show_form(step_id="user")
