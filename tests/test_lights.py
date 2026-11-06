# SPDX-License-Identifier: GPL-3.0-or-later
"""The adjust_light action."""

from __future__ import annotations

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.bilresa_dimmer.const import DOMAIN, TURN_GAP_S

LIGHT = "light.desk"


@pytest.fixture
async def setup(hass):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, DOMAIN, {})
    return async_mock_service(hass, "light", "turn_on")


async def adjust(hass, **data):
    data = {"entity_id": LIGHT, "attribute": "brightness", **data}
    await hass.services.async_call(DOMAIN, "adjust_light", data, blocking=True)
    await hass.async_block_till_done()


def light(hass, state: str, **attributes) -> None:
    hass.states.async_set(LIGHT, state, attributes)


def sent(calls):
    return [{k: v for k, v in c.data.items() if k != "entity_id"} for c in calls]


async def test_brightness_moves_by_steps_of_the_given_percent_with_a_fade(hass, setup):
    light(hass, "on", brightness=128)  # 50 %
    await adjust(hass, steps=1, percent=5)
    assert sent(setup) == [{"brightness_pct": 55, "transition": 0.3}]


async def test_the_step_size_and_fade_are_set_by_the_caller(hass, setup):
    light(hass, "on", brightness=128)
    await adjust(hass, steps=-3, percent=10, transition=1.5)
    assert sent(setup) == [{"brightness_pct": 20, "transition": 1.5}]


async def test_the_step_size_defaults_to_five_percent(hass, setup):
    light(hass, "on", brightness=128)
    await adjust(hass, steps=2)
    assert sent(setup)[0]["brightness_pct"] == 60


async def test_the_next_call_builds_on_what_was_asked_not_on_a_light_still_fading(hass, setup):
    light(hass, "on", brightness=128)
    await adjust(hass, steps=1)
    await adjust(hass, steps=1)  # the light still reports 50 %
    assert [c["brightness_pct"] for c in sent(setup)] == [55, 60]


async def test_the_light_is_read_again_when_the_wheel_was_idle(hass, setup, monkeypatch):
    light(hass, "on", brightness=128)
    await adjust(hass, steps=1)
    now = hass.loop.time()
    monkeypatch.setattr(hass.loop, "time", lambda: now + TURN_GAP_S + 1)  # a pause; the light was changed meanwhile
    light(hass, "on", brightness=255)
    await adjust(hass, steps=-1)
    assert [c["brightness_pct"] for c in sent(setup)] == [55, 95]


async def test_dimming_never_turns_the_light_off_and_brightening_stops_at_full(hass, setup):
    light(hass, "on", brightness=8)  # 3 %
    await adjust(hass, steps=-1)
    hass.states.async_set("light.other", "on", {"brightness": 250})
    await adjust(hass, steps=1, entity_id="light.other")
    assert [c["brightness_pct"] for c in sent(setup)] == [1, 100]


async def test_a_positive_change_switches_an_off_light_on_and_a_negative_one_leaves_it_off(hass, setup):
    light(hass, "off")
    await adjust(hass, steps=-1)
    assert setup == []
    await adjust(hass, steps=2)
    assert [c["brightness_pct"] for c in sent(setup)] == [10]


async def test_lights_that_cannot_be_dimmed_or_are_unavailable_are_left_alone(hass, setup):
    light(hass, "on")
    await adjust(hass, steps=1)
    light(hass, "unavailable")
    await adjust(hass, steps=1)
    await adjust(hass, steps=1, entity_id="light.missing")
    assert setup == []


async def test_colour_temperature_moves_by_a_percentage_of_the_lights_range(hass, setup):
    light(hass, "on", color_temp_kelvin=4000, min_color_temp_kelvin=2000, max_color_temp_kelvin=6500)
    await adjust(hass, attribute="color_temp", steps=2, percent=5)  # 10 % of 4500 K
    assert sent(setup) == [{"color_temp_kelvin": 4450, "transition": 0.3}]


async def test_colour_temperature_stays_inside_the_lights_range(hass, setup):
    light(hass, "on", color_temp_kelvin=6400, min_color_temp_kelvin=2000, max_color_temp_kelvin=6500)
    await adjust(hass, attribute="color_temp", steps=10, percent=10)
    assert sent(setup)[0]["color_temp_kelvin"] == 6500


async def test_colour_temperature_leaves_off_lights_and_lights_showing_a_colour_alone(hass, setup):
    light(hass, "off", min_color_temp_kelvin=2000, max_color_temp_kelvin=6500)
    await adjust(hass, attribute="color_temp", steps=1)
    light(hass, "on", color_temp_kelvin=None, min_color_temp_kelvin=2000, max_color_temp_kelvin=6500)
    await adjust(hass, attribute="color_temp", steps=1)
    assert setup == []


async def test_brightness_and_colour_temperature_are_remembered_separately(hass, setup):
    light(hass, "on", brightness=128, color_temp_kelvin=4000, min_color_temp_kelvin=2000, max_color_temp_kelvin=6500)
    await adjust(hass, steps=1)
    await adjust(hass, attribute="color_temp", steps=1)
    assert [set(v) - {"transition"} for v in sent(setup)] == [{"brightness_pct"}, {"color_temp_kelvin"}]
    assert sent(setup)[1]["color_temp_kelvin"] == 4225


async def test_only_lights_are_moved_when_the_target_names_other_entities(hass, setup):
    light(hass, "on", brightness=128)
    hass.states.async_set("switch.lamp", "on")
    await adjust(hass, steps=1, entity_id=[LIGHT, "switch.lamp"])
    assert [c.data["entity_id"] for c in setup] == [LIGHT]


@pytest.mark.parametrize(
    "bad", [{"attribute": "hue"}, {"percent": 0}, {"percent": 101}, {"steps": 1000}, {"transition": -1}, {"steps": "x"}]
)
async def test_values_outside_what_is_allowed_are_refused(hass, setup, bad):
    light(hass, "on", brightness=128)
    with pytest.raises(vol.Invalid):
        await adjust(hass, **{"steps": 1, **bad})
    assert setup == []
