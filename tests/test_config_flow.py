# SPDX-License-Identifier: GPL-3.0-or-later
"""Setting the integration up."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bilresa_dimmer.const import DOMAIN


async def start(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})


async def test_setup_is_one_confirmation_with_no_settings(hass, fast_matter_switch):
    result = await start(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user" and not result["data_schema"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["data"] == {}


async def test_setup_needs_fast_matter_switch(hass):
    result = await start(hass)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "no_fast_matter_switch"


async def test_it_is_set_up_once(hass, entry):
    result = await start(hass)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "single_instance_allowed"


async def test_without_fast_matter_switch_setup_waits(hass, area):
    from homeassistant.config_entries import ConfigEntryState
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    config = MockConfigEntry(domain=DOMAIN, data={})
    config.add_to_hass(hass)
    await hass.config_entries.async_setup(config.entry_id)
    assert config.state is ConfigEntryState.SETUP_RETRY
