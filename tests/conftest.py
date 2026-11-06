# SPDX-License-Identifier: GPL-3.0-or-later
"""A Matter dimmer device with its nine buttons, and Fast Matter switch set up."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bilresa_dimmer.const import DOMAIN, FAST_MATTER_SWITCH_DOMAIN

MODE_1 = "event.living_room_bilresa_dimmer_mode_1"
MODE_2 = "event.living_room_bilresa_dimmer_mode_2"
MODE_3 = "event.living_room_bilresa_dimmer_mode_3"


@pytest.fixture(autouse=True)
def _custom_integrations(enable_custom_integrations):
    """Lets Home Assistant load custom_components/bilresa_dimmer."""


@pytest.fixture
def fast_matter_switch(hass):
    entry = MockConfigEntry(domain=FAST_MATTER_SWITCH_DOMAIN, state=ConfigEntryState.LOADED)
    entry.add_to_hass(hass)
    return entry


def make_matter_device(hass, buttons: int = 9, name: str = "Living Room Bilresa Dimmer", area_id: str | None = None):
    """A Matter device with ``buttons`` event entities, named as the Matter integration names them."""
    matter = MockConfigEntry(domain="matter")
    matter.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(config_entry_id=matter.entry_id, identifiers={("matter", name)}, name=name)
    if area_id:
        dr.async_get(hass).async_update_device(device.id, area_id=area_id)
    for endpoint in range(1, buttons + 1):
        er.async_get(hass).async_get_or_create(
            "event", "matter", f"FABRIC-{name}-{endpoint}", config_entry=matter, device_id=device.id, original_name=f"Button ({endpoint})"
        )
    return device


@pytest.fixture
def area(hass):
    return ar.async_get(hass).async_create("Living room")


@pytest.fixture
def dimmer(hass, area):
    return make_matter_device(hass, area_id=area.id)


@pytest.fixture
async def entry(hass, fast_matter_switch, dimmer):
    """The integration set up with one dimmer."""
    config = MockConfigEntry(domain=DOMAIN, title="IKEA BILRESA dimmer", data={})
    config.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config.entry_id)
    await hass.async_block_till_done()
    return config
