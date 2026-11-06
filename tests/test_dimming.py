# SPDX-License-Identifier: GPL-3.0-or-later
"""How many steps a wheel click counts for."""

from __future__ import annotations

import pytest

from custom_components.bilresa_dimmer.const import SEQUENCE_TIMEOUT_S, TURN_GAP_S
from custom_components.bilresa_dimmer.dimming import ClickCounter, Turn, multiplier


@pytest.mark.parametrize(
    ("clicks", "steps"),
    [(1, 1), (3, 1), (4, 2), (8, 2), (9, 3), (100, 3)],
)
def test_clicks_count_for_more_the_longer_a_turn_goes_on(clicks, steps):
    assert multiplier(clicks) == steps


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_a_turn_speeds_up_click_by_click():
    turn = Turn(Clock())
    assert [turn.click(1) for _ in range(10)] == [1, 1, 1, 2, 2, 2, 2, 2, 3, 3]


def test_counter_clockwise_is_negative_and_speeds_up_the_same_way():
    turn = Turn(Clock())
    assert [turn.click(-1) for _ in range(4)] == [-1, -1, -1, -2]


def test_a_pause_starts_a_new_turn():
    clock = Clock()
    turn = Turn(clock)
    assert [turn.click(1) for _ in range(5)] == [1, 1, 1, 2, 2]
    clock.now += TURN_GAP_S + 0.1
    assert turn.click(1) == 1


def test_clicks_just_inside_the_pause_continue_the_turn():
    clock = Clock()
    turn = Turn(clock)
    for _ in range(3):
        turn.click(1)
    clock.now += TURN_GAP_S
    assert turn.click(1) == 2


def test_turning_the_other_way_starts_a_new_turn():
    turn = Turn(Clock())
    for _ in range(5):
        turn.click(1)
    assert turn.click(-1) == -1


def replay(counter: ClickCounter, events: list[tuple[str, int | None]]) -> list[int]:
    """The new clicks each event adds: ("initial_press", None), ("ongoing", presses) or ("complete", presses)."""
    new = []
    for kind, presses in events:
        if kind == "initial_press":
            new.append(counter.initial_press())
        else:
            new.append(counter.total(presses, complete=kind == "complete"))
    return new


def test_a_fast_turn_counts_the_clicks_the_dimmer_counted_not_its_initial_presses():
    # From the owner's dimmer, 2026-11-06: four initial presses, but 18 clicks.
    events = [
        ("initial_press", None),
        ("initial_press", None),
        ("ongoing", 8),
        ("initial_press", None),
        ("ongoing", 14),
        ("initial_press", None),
        ("ongoing", 18),
        ("complete", 18),
    ]
    assert sum(replay(ClickCounter(Clock()), events)) == 18


def test_a_slow_turn_counts_a_click_at_every_initial_press_and_the_counts_add_nothing():
    # Also from the dimmer: five clicks, one at a time.
    events = [
        ("initial_press", None),
        ("complete", 1),
        ("initial_press", None),
        ("complete", 1),
        ("initial_press", None),
        ("initial_press", None),
        ("ongoing", 2),
        ("initial_press", None),
        ("ongoing", 3),
        ("complete", 3),
    ]
    new = replay(ClickCounter(Clock()), events)
    assert new == [1, 0, 1, 0, 1, 1, 0, 1, 0, 0]


def test_the_next_sequence_counts_from_zero():
    counter = ClickCounter(Clock())
    assert sum(replay(counter, [("initial_press", None), ("ongoing", 7), ("complete", 7)])) == 7
    assert sum(replay(counter, [("initial_press", None), ("ongoing", 3), ("complete", 3)])) == 3


def test_a_sequence_whose_closing_event_never_came_is_dropped_after_a_pause():
    clock = Clock()
    counter = ClickCounter(clock)
    assert sum(replay(counter, [("initial_press", None), ("ongoing", 5)])) == 5
    clock.now += SEQUENCE_TIMEOUT_S + 0.1
    assert sum(replay(counter, [("initial_press", None), ("ongoing", 2)])) == 2


def test_a_count_below_what_is_already_counted_adds_nothing():
    counter = ClickCounter(Clock())
    assert sum(replay(counter, [("initial_press", None), ("initial_press", None), ("ongoing", 1)])) == 2


def test_an_unbelievable_jump_is_limited():
    assert ClickCounter(Clock()).total(5000, complete=False) == 100
