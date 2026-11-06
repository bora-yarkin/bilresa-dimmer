# SPDX-License-Identifier: GPL-3.0-or-later
"""What the dimmer's events do to the lights."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed, async_mock_service

from custom_components.bilresa_dimmer.const import BATCH_S, DOMAIN, FAST_EVENT, TRANSITION_S

from .conftest import LIGHT, OTHER_LIGHT

CCW, CW, PRESS = 0, 1, 2


def endpoint(mode: int, button: int) -> int:
    return (mode - 1) * 3 + button + 1


def click(hass, dimmer, mode: int, button: int, event_type: str = "initial_press", **extra) -> None:
    hass.bus.async_fire(
        FAST_EVENT, {"event_type": event_type, "device_id": dimmer.id, "endpoint_id": endpoint(mode, button), "node_id": 62, **extra}
    )


async def batch_ends(hass) -> None:
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=BATCH_S + 1))
    await hass.async_block_till_done()


def light_is(hass, entity_id: str, state: str, brightness: int | None = None) -> None:
    hass.states.async_set(entity_id, state, {} if brightness is None else {"brightness": brightness})


def percents(calls) -> list[int]:
    return [c.data["brightness_pct"] for c in calls]


async def test_a_click_clockwise_brightens_with_a_short_fade(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)  # 50 %
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert len(calls) == 1
    assert calls[0].data == {"entity_id": LIGHT, "brightness_pct": 55, "transition": TRANSITION_S}


async def test_a_click_counter_clockwise_dims(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    click(hass, dimmer, 1, CCW)
    await batch_ends(hass)
    assert percents(calls) == [45]


async def test_clicks_that_arrive_together_make_one_change(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    for _ in range(3):
        click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert percents(calls) == [65]


async def test_the_next_batch_builds_on_what_was_asked_not_on_a_light_still_fading(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    click(hass, dimmer, 1, CW)  # the light still reports 50 %: its fade has not got anywhere yet
    await batch_ends(hass)
    assert percents(calls) == [55, 60]


async def test_a_turn_speeds_up_across_batches(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 26)  # 10 %
    for _ in range(5):
        click(hass, dimmer, 1, CW)
        await batch_ends(hass)
    assert percents(calls) == [15, 20, 25, 35, 45]


async def test_dimming_never_turns_the_light_off(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 8)  # 3 %
    click(hass, dimmer, 1, CCW)
    await batch_ends(hass)
    assert percents(calls) == [1]


async def test_brightening_stops_at_full(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 250)
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert percents(calls) == [100]


async def test_clockwise_switches_an_off_light_on_at_the_first_step_and_counter_clockwise_leaves_it_off(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "off")
    click(hass, dimmer, 1, CCW)
    await batch_ends(hass)
    assert calls == []
    click(hass, dimmer, 1, CW)  # a new direction starts a new turn
    await batch_ends(hass)
    assert percents(calls) == [5]


async def test_lights_that_cannot_be_dimmed_or_are_unavailable_are_left_alone(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on")  # on, no brightness
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    light_is(hass, LIGHT, "unavailable")
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert calls == []


async def test_each_mode_has_its_own_buttons_and_lights(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    light_is(hass, OTHER_LIGHT, "on", 128)
    click(hass, dimmer, 2, CW)  # endpoint 5
    await batch_ends(hass)
    assert [(c.data["entity_id"], c.data["brightness_pct"]) for c in calls] == [(OTHER_LIGHT, 55)]


async def test_a_mode_with_no_lights_does_nothing(hass, entry, dimmer):
    on = async_mock_service(hass, "light", "turn_on")
    toggle = async_mock_service(hass, "light", "toggle")
    click(hass, dimmer, 3, CW)
    click(hass, dimmer, 3, PRESS, fast_event_type="press")
    await batch_ends(hass)
    assert on == [] and toggle == []


async def test_the_wheel_press_toggles_the_lights_of_the_mode(hass, entry, dimmer):
    toggle = async_mock_service(hass, "light", "toggle")
    click(hass, dimmer, 1, PRESS, fast_event_type="press")
    await hass.async_block_till_done()
    assert [c.data for c in toggle] == [{"entity_id": [LIGHT]}]


async def test_only_a_press_toggles_not_the_second_touch_of_a_double_press_or_a_release(hass, entry, dimmer):
    toggle = async_mock_service(hass, "light", "toggle")
    click(hass, dimmer, 1, PRESS)  # the second touch of a double press: Fast Matter switch gives it no fast_event_type
    click(hass, dimmer, 1, PRESS, "short_release")
    click(hass, dimmer, 1, PRESS, "long_press", fast_event_type="long_press")
    await hass.async_block_till_done()
    assert toggle == []


async def test_a_press_forgets_the_brightness_it_was_building_on(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    async_mock_service(hass, "light", "toggle")
    light_is(hass, LIGHT, "on", 128)
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    click(hass, dimmer, 1, PRESS, fast_event_type="press")
    await hass.async_block_till_done()
    light_is(hass, LIGHT, "on", 255)  # switched off and on again at full
    click(hass, dimmer, 1, CCW)
    await batch_ends(hass)
    assert percents(calls) == [55, 95]


async def test_events_the_wheel_does_not_use_are_ignored(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    for event_type in ("short_release", "multi_press_ongoing", "multi_press_complete", "long_press", "long_release"):
        click(hass, dimmer, 1, CW, event_type)
    await batch_ends(hass)
    assert calls == []


async def test_other_devices_and_unreadable_events_are_ignored(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press", "device_id": "someone-else", "endpoint_id": 2})
    for bad in (0, 10, "2", None, True):
        hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press", "device_id": dimmer.id, "endpoint_id": bad})
    hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press"})
    await batch_ends(hass)
    assert calls == []


async def test_unloading_drops_clicks_that_have_not_been_applied_and_stops_listening(hass, entry, dimmer):
    calls = async_mock_service(hass, "light", "turn_on")
    light_is(hass, LIGHT, "on", 128)
    click(hass, dimmer, 1, CW)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await batch_ends(hass)
    click(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert calls == []


async def test_without_fast_matter_switch_setup_waits(hass, dimmer):
    config = MockConfigEntry(domain=DOMAIN, data={"device_id": dimmer.id})
    config.add_to_hass(hass)
    await hass.config_entries.async_setup(config.entry_id)
    assert config.state is ConfigEntryState.SETUP_RETRY
