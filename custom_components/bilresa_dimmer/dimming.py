# SPDX-License-Identifier: GPL-3.0-or-later
"""How far one wheel click moves the brightness. Pure logic: no Home Assistant, no clock of its own."""

from __future__ import annotations

from collections.abc import Callable

from .const import STEPS, TURN_GAP_S


def step_percent(clicks_in_turn: int) -> int:
    """The step of the n-th click (counting from 1) of a turn: small at first, larger the longer the turn goes on."""
    for limit, percent in STEPS:
        if limit is None or clicks_in_turn <= limit:
            return percent
    raise AssertionError("STEPS must end with an unlimited step")  # pragma: no cover


class Turn:
    """Follows the clicks of one wheel (one mode of one dimmer) and says how far each one moves the brightness.

    A turn is a run of clicks in one direction with no pause longer than ``TURN_GAP_S``. A pause or a change of direction
    starts a new turn, so a slow, careful adjustment moves in small steps and a long quick spin covers the range.
    """

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._direction = 0
        self._last = float("-inf")
        self._clicks = 0

    def click(self, direction: int) -> int:
        """The signed percentage for one click; ``direction`` is +1 (brighter) or -1 (dimmer)."""
        now = self._clock()
        if direction != self._direction or now - self._last > TURN_GAP_S:
            self._direction = direction
            self._clicks = 0
        self._last = now
        self._clicks += 1
        return direction * step_percent(self._clicks)
