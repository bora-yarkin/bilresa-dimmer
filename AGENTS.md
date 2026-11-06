# IKEA BILRESA dimmer: project instructions

- Domain `bilresa_dimmer`. One config entry per dimmer (the Matter device with nine buttons). `__init__.py`: `DimmerController` listens to
  Fast Matter switch's `fast_matter_switch_event` bus events and calls `light.turn_on` / `light.toggle`. `dimming.py`: pure step logic
  (`Turn`). `config_flow.py`: pick the device, then the lights of modes 1 to 3 (also the options flow). `const.py`: button layout and tuning.
- Button layout, from the owner's description and a capture of the real dimmer on 2026-11-06: buttons 1 to 9 are Matter endpoints 1 to 9;
  per mode, in order: counter-clockwise, clockwise, wheel press. The mode button sends no event. Every wheel click is an `initial_press`
  of its direction button, arriving at once; the dimmer's radio sends quick clicks in a burst (several within milliseconds), and its
  `multi_press_complete` count is unreliable, so only `initial_press` is used for the wheel. The wheel press uses Fast Matter switch's
  `fast_event_type == "press"` (needs Fast Matter switch 0.5.0 or later).
- Tests: `uv venv --python 3.14 .venv && uv pip install --python .venv/bin/python pytest-homeassistant-custom-component==0.13.375 ruff`, then
  `.venv/bin/python -m pytest` and `.venv/bin/ruff check . && .venv/bin/ruff format --check .`. Nothing is mocked inside the integration;
  the light services are recorded.
- No dependency beyond Home Assistant. Licence GPL-3.0-or-later; Python files start with the SPDX line. Private and local until the owner
  says to publish.
