# SPDX-License-Identifier: GPL-3.0-or-later
"""Constants for the IKEA BILRESA dimmer."""

DOMAIN = "bilresa_dimmer"
MATTER_DOMAIN = "matter"
FAST_MATTER_SWITCH_DOMAIN = "fast_matter_switch"

# Fired by Fast Matter switch for every Matter Generic Switch event.
FAST_EVENT = "fast_matter_switch_event"

# The dimmer has three modes (the mode button switches between them) and each mode has three Matter buttons: wheel clockwise,
# wheel counter-clockwise and wheel press. The buttons are numbered 1 to 9 in that order, and a button's number is its Matter
# endpoint, so endpoint 5 is counter-clockwise in mode 2. (The order was checked on the owner's dimmer on 2026-11-06.)
MODES = (1, 2, 3)
BUTTONS_PER_MODE = 3
BUTTON_COUNT = BUTTONS_PER_MODE * len(MODES)
CLOCKWISE, COUNTER_CLOCKWISE, PRESS = 0, 1, 2

# What a mode's event entity reports.
EVENT_CLOCKWISE = "clockwise"
EVENT_COUNTER_CLOCKWISE = "counter_clockwise"
EVENT_PRESS = "press"
EVENT_DOUBLE_PRESS = "double_press"
EVENT_LONG_PRESS = "long_press"
EVENT_TYPES = [EVENT_CLOCKWISE, EVENT_COUNTER_CLOCKWISE, EVENT_PRESS, EVENT_DOUBLE_PRESS, EVENT_LONG_PRESS]
# The press events Fast Matter switch reports (its ``fast_event_type``) are passed on under the same names.
PRESS_EVENT_TYPES = (EVENT_PRESS, EVENT_DOUBLE_PRESS, EVENT_LONG_PRESS)

ATTR_STEPS = "steps"

# The n-th click of a turn counts for this many steps: (up to this many clicks, steps); the last has no limit.
MULTIPLIERS = ((3, 1), (8, 2), (None, 3))
# A pause this long ends a turn; the next click starts again with the smallest step.
TURN_GAP_S = 1.0
# The dimmer's radio sends quick clicks together; clicks that arrive within this time are reported as one event.
BATCH_S = 0.05

# adjust_light
SERVICE_ADJUST_LIGHT = "adjust_light"
ATTR_ATTRIBUTE = "attribute"
ATTR_PERCENT = "percent"
ATTR_TRANSITION = "transition"
BRIGHTNESS = "brightness"
COLOR_TEMP = "color_temp"
DEFAULT_PERCENT = 5.0
DEFAULT_TRANSITION_S = 0.3
MIN_BRIGHTNESS_PCT = 1
