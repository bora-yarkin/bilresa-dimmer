# SPDX-License-Identifier: GPL-3.0-or-later
"""How many steps a wheel click counts for."""

from __future__ import annotations

import pytest

from custom_components.bilresa_dimmer.const import TURN_GAP_S
from custom_components.bilresa_dimmer.dimming import Turn, multiplier


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
