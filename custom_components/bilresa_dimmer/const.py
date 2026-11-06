# SPDX-License-Identifier: GPL-3.0-or-later
"""Constants for the IKEA BILRESA dimmer."""

DOMAIN = "bilresa_dimmer"
MATTER_DOMAIN = "matter"
FAST_MATTER_SWITCH_DOMAIN = "fast_matter_switch"

# Fired by Fast Matter switch for every Matter Generic Switch event.
FAST_EVENT = "fast_matter_switch_event"

CONF_DEVICE_ID = "device_id"
MODES = (1, 2, 3)


def conf_lights(mode: int) -> str:
    """The option that holds the lights of one mode."""
    return f"mode_{mode}_lights"


# The dimmer has three modes (the mode button switches between them) and each mode has three Matter buttons:
# counter-clockwise, clockwise, and the wheel press. The buttons are numbered 1 to 9 in that order, and a button's number
# is its Matter endpoint, so endpoint 5 is clockwise in mode 2.
BUTTONS_PER_MODE = 3
BUTTON_COUNT = BUTTONS_PER_MODE * len(MODES)
COUNTER_CLOCKWISE, CLOCKWISE, PRESS = 0, 1, 2

# One wheel click moves the brightness by a step that grows as a turn goes on (see dimming.py).
STEPS = ((3, 5), (8, 10), (None, 15))  # (up to this many clicks, percent); the last step has no limit
# A pause this long ends a turn; the next click starts again with the smallest step.
TURN_GAP_S = 1.0
# The dimmer's radio sends quick clicks together; clicks that arrive within this time are applied as one change.
BATCH_S = 0.05
# The fade between the old and the new brightness.
TRANSITION_S = 0.3
MIN_BRIGHTNESS_PCT = 1
