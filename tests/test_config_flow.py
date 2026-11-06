# SPDX-License-Identifier: GPL-3.0-or-later
"""Setting up a dimmer and changing its lights."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bilresa_dimmer.const import CONF_DEVICE_ID, DOMAIN, conf_lights

from .conftest import LIGHT, OTHER_LIGHT, make_matter_device


async def start(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})


async def test_a_dimmer_is_set_up_with_the_lights_of_its_modes(hass, fast_matter_switch, dimmer):
    result = await start(hass)
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: dimmer.id})
    assert result["step_id"] == "lights"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {conf_lights(1): [LIGHT], conf_lights(2): [OTHER_LIGHT]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room Bilresa Dimmer"
    assert result["data"] == {CONF_DEVICE_ID: dimmer.id}
    assert result["result"].options == {conf_lights(1): [LIGHT], conf_lights(2): [OTHER_LIGHT], conf_lights(3): []}


async def test_the_first_mode_needs_a_light(hass, fast_matter_switch, dimmer):
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: dimmer.id})
    schema = result["data_schema"].schema
    required = {str(key) for key in schema if key.__class__.__name__ == "Required"}
    assert required == {conf_lights(1)}


async def test_a_matter_device_without_nine_buttons_is_refused(hass, fast_matter_switch):
    two_buttons = make_matter_device(hass, buttons=2, name="Entrance Switch")
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: two_buttons.id})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    assert result["errors"] == {"base": "not_a_dimmer"}


async def test_a_dimmer_is_set_up_once(hass, entry, dimmer):
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: dimmer.id})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_setup_needs_fast_matter_switch(hass, dimmer):
    result = await start(hass)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "no_fast_matter_switch"


async def test_the_lights_of_the_modes_can_be_changed_later(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {conf_lights(1): [OTHER_LIGHT], conf_lights(3): [LIGHT]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {conf_lights(1): [OTHER_LIGHT], conf_lights(2): [], conf_lights(3): [LIGHT]}
