# SPDX-License-Identifier: GPL-3.0-or-later
"""What the dimmer's events become on its mode entities."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.bilresa_dimmer.const import BATCH_S, FAST_EVENT

from .conftest import MODE_1, MODE_2, MODE_3, make_matter_device

CW, CCW, PRESS = 0, 1, 2


def endpoint(mode: int, button: int) -> int:
    return (mode - 1) * 3 + button + 1


def send(hass, dimmer, mode: int, button: int, event_type: str = "initial_press", **extra) -> None:
    hass.bus.async_fire(
        FAST_EVENT, {"event_type": event_type, "device_id": dimmer.id, "endpoint_id": endpoint(mode, button), "node_id": 62, **extra}
    )


async def batch_ends(hass) -> None:
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=BATCH_S + 1))
    await hass.async_block_till_done()


def reported(hass, entity_id: str) -> tuple[str, int | None]:
    attributes = hass.states.get(entity_id).attributes
    return attributes["event_type"], attributes.get("steps")


async def test_a_dimmer_gets_an_entity_for_each_mode_named_after_it_in_its_area(hass, entry, dimmer, area):
    registry = er.async_get(hass)
    for entity_id, mode in ((MODE_1, 1), (MODE_2, 2), (MODE_3, 3)):
        entity = registry.async_get(entity_id)
        assert entity.unique_id == f"{dimmer.id}-mode-{mode}" and entity.area_id == area.id
        assert hass.states.get(entity_id).attributes["friendly_name"] == f"Living Room Bilresa Dimmer mode {mode}"
    assert hass.states.get(MODE_1).attributes["event_types"] == ["clockwise", "counter_clockwise", "press", "double_press", "long_press"]


async def test_only_a_device_with_nine_matter_buttons_is_a_dimmer(hass, entry):
    make_matter_device(hass, buttons=2, name="Entrance Switch")
    await hass.async_block_till_done()
    assert hass.states.get("event.entrance_switch_mode_1") is None


async def test_a_dimmer_added_later_gets_its_entities(hass, entry):
    make_matter_device(hass, name="Bedroom Dimmer")
    await hass.async_block_till_done()
    assert hass.states.get("event.bedroom_dimmer_mode_1") is not None


async def test_a_click_is_reported_with_one_step_and_the_direction(hass, entry, dimmer):
    send(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert reported(hass, MODE_1) == ("clockwise", 1)
    send(hass, dimmer, 1, CCW)
    await batch_ends(hass)
    assert reported(hass, MODE_1) == ("counter_clockwise", -1)


async def test_clicks_that_arrive_together_are_one_event_with_their_steps_added_up(hass, entry, dimmer):
    states = []
    hass.bus.async_listen("state_changed", lambda e: states.append(e) if e.data["entity_id"] == MODE_1 else None)
    for _ in range(3):
        send(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert reported(hass, MODE_1) == ("clockwise", 3)
    assert len(states) == 1


async def test_a_turn_speeds_up_across_events(hass, entry, dimmer):
    seen = []
    for _ in range(5):
        send(hass, dimmer, 1, CW)
        await batch_ends(hass)
        seen.append(reported(hass, MODE_1)[1])
    assert seen == [1, 1, 1, 2, 2]


async def test_clicks_in_opposite_directions_that_cancel_report_nothing(hass, entry, dimmer):
    send(hass, dimmer, 1, CW)
    send(hass, dimmer, 1, CCW)
    await batch_ends(hass)
    assert hass.states.get(MODE_1).state == "unknown"


async def test_each_mode_uses_its_own_buttons(hass, entry, dimmer):
    send(hass, dimmer, 2, CCW)  # endpoint 5
    await batch_ends(hass)
    assert reported(hass, MODE_2) == ("counter_clockwise", -1)
    assert hass.states.get(MODE_1).state == "unknown" and hass.states.get(MODE_3).state == "unknown"


async def test_the_wheel_press_is_reported_as_fast_matter_switch_decides(hass, entry, dimmer):
    for fast in ("press", "double_press", "long_press"):
        send(hass, dimmer, 3, PRESS, fast_event_type=fast)
        await hass.async_block_till_done()
        assert reported(hass, MODE_3) == (fast, None)


async def test_the_second_touch_of_a_double_press_and_releases_are_not_reported(hass, entry, dimmer):
    send(hass, dimmer, 1, PRESS)  # no fast_event_type: Fast Matter switch gives the second touch none
    send(hass, dimmer, 1, PRESS, "short_release")
    await batch_ends(hass)
    assert hass.states.get(MODE_1).state == "unknown"


async def test_events_the_wheel_does_not_use_are_ignored(hass, entry, dimmer):
    for event_type in ("short_release", "multi_press_ongoing", "multi_press_complete", "long_press", "long_release"):
        send(hass, dimmer, 1, CW, event_type)
    await batch_ends(hass)
    assert hass.states.get(MODE_1).state == "unknown"


async def test_other_devices_and_unreadable_events_are_ignored(hass, entry, dimmer):
    hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press", "device_id": "someone-else", "endpoint_id": 1})
    for bad in (0, 10, "2", None, True):
        hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press", "device_id": dimmer.id, "endpoint_id": bad})
    hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press", "endpoint_id": 1})
    hass.bus.async_fire(FAST_EVENT, {"event_type": "initial_press", "device_id": 5, "endpoint_id": 1})
    await batch_ends(hass)
    assert hass.states.get(MODE_1).state == "unknown"


async def test_unloading_drops_clicks_not_yet_reported_and_stops_listening(hass, entry, dimmer):
    send(hass, dimmer, 1, CW)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await batch_ends(hass)
    send(hass, dimmer, 1, CW)
    await batch_ends(hass)
    assert hass.states.get(MODE_1).state == "unavailable"
