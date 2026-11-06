# SPDX-License-Identifier: GPL-3.0-or-later
"""How far a wheel click moves the brightness."""

from __future__ import annotations

import pytest

from custom_components.bilresa_dimmer.const import TURN_GAP_S
from custom_components.bilresa_dimmer.dimming import Turn, step_percent


@pytest.mark.parametrize(
    ("clicks", "percent"),
    [(1, 5), (3, 5), (4, 10), (8, 10), (9, 15), (100, 15)],
)
def test_steps_grow_the_longer_a_turn_goes_on(clicks, percent):
    assert step_percent(clicks) == percent


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_a_turn_speeds_up_click_by_click():
    clock = Clock()
    turn = Turn(clock)
    assert [turn.click(1) for _ in range(10)] == [5, 5, 5, 10, 10, 10, 10, 10, 15, 15]


def test_dimming_is_negative_and_has_its_own_run():
    clock = Clock()
    turn = Turn(clock)
    assert [turn.click(-1) for _ in range(4)] == [-5, -5, -5, -10]


def test_a_pause_starts_a_new_turn_with_the_smallest_step():
    clock = Clock()
    turn = Turn(clock)
    assert [turn.click(1) for _ in range(5)] == [5, 5, 5, 10, 10]
    clock.now += TURN_GAP_S + 0.1
    assert turn.click(1) == 5


def test_clicks_just_inside_the_pause_continue_the_turn():
    clock = Clock()
    turn = Turn(clock)
    for _ in range(3):
        turn.click(1)
    clock.now += TURN_GAP_S
    assert turn.click(1) == 10


def test_turning_the_other_way_starts_a_new_turn():
    clock = Clock()
    turn = Turn(clock)
    for _ in range(5):
        turn.click(1)
    assert turn.click(-1) == -5
