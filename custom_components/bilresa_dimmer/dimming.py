# SPDX-License-Identifier: GPL-3.0-or-later
"""How many steps one wheel click counts for. Pure logic: no Home Assistant, no clock of its own."""

from __future__ import annotations

from collections.abc import Callable

from .const import MULTIPLIERS, TURN_GAP_S


def multiplier(clicks_in_turn: int) -> int:
    """The steps of the n-th click (counting from 1) of a turn: one at first, more the longer the turn goes on."""
    for limit, steps in MULTIPLIERS:
        if limit is None or clicks_in_turn <= limit:
            return steps
    raise AssertionError("MULTIPLIERS must end with an unlimited step")  # pragma: no cover


class Turn:
    """Follows the clicks of one wheel (one mode of one dimmer) and says how many steps each one counts for.

    A turn is a run of clicks in one direction with no pause longer than ``TURN_GAP_S``. A pause or a change of direction
    starts a new turn, so a slow, careful adjustment moves in single steps and a long quick spin covers the range.
    """

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._direction = 0
        self._last = float("-inf")
        self._clicks = 0

    def click(self, direction: int) -> int:
        """The signed steps of one click; ``direction`` is +1 (clockwise) or -1 (counter-clockwise)."""
        now = self._clock()
        if direction != self._direction or now - self._last > TURN_GAP_S:
            self._direction = direction
            self._clicks = 0
        self._last = now
        self._clicks += 1
        return direction * multiplier(self._clicks)
