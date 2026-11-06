# SPDX-License-Identifier: GPL-3.0-or-later
"""How many steps one wheel click counts for. Pure logic: no Home Assistant, no clock of its own."""

from __future__ import annotations

from collections.abc import Callable

from .const import MAX_CLICKS_PER_EVENT, MULTIPLIERS, SEQUENCE_TIMEOUT_S, TURN_GAP_S


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


class ClickCounter:
    """Counts the wheel clicks of one direction from the dimmer's multi-press events.

    A fast turn is not reported click by click. The dimmer sends an ``initial_press`` only every half second or so, and the real
    number of clicks so far is in the ``presses`` count of the ``multi_press_ongoing`` events that follow (8, then 14, then 18, say);
    the closing ``multi_press_complete`` repeats the total. A slow turn does send one ``initial_press`` per click. So an
    ``initial_press`` counts as one click at once, and a count tops the clicks up to the dimmer's own total. The total is for one
    sequence; ``multi_press_complete`` ends it.
    """

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._counted = 0
        self._last = float("-inf")

    def _touch(self) -> None:
        now = self._clock()
        if now - self._last > SEQUENCE_TIMEOUT_S:  # the closing event never came
            self._counted = 0
        self._last = now

    def initial_press(self) -> int:
        """The new clicks since the last event: one."""
        self._touch()
        self._counted += 1
        return 1

    def total(self, presses: int | None, *, complete: bool) -> int:
        """The new clicks when the dimmer says ``presses`` clicks were made in this sequence (None when it did not say)."""
        self._touch()
        new = 0
        if presses is not None and presses > self._counted:
            new = min(presses - self._counted, MAX_CLICKS_PER_EVENT)
            self._counted = presses
        if complete:
            self._counted = 0
        return new
