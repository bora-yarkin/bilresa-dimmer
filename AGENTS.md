# IKEA BILRESA dimmer: project instructions

- Domain `bilresa_dimmer`. A single config entry with no settings (`config_flow.py`). `events.py`: `DimmerEvents` listens to Fast Matter
  switch's `fast_matter_switch_event` bus events, adds up the steps of wheel clicks that arrive within 50 ms and dispatches them; `event.py`:
  three event entities per dimmer (a Matter device with exactly nine Matter event entities), `clockwise` / `counter_clockwise` with a
  `steps` attribute, and the wheel press types; `dimming.py`: pure step logic (`Turn`); `lights.py` and `__init__.py`: the
  `bilresa_dimmer.adjust_light` action. What a mode controls is decided in the user's automations, never in the integration (owner's decision,
  2026-11-06).
- Button layout, from a capture of the real dimmer on 2026-11-06 and the owner's test: buttons 1 to 9 are Matter endpoints 1 to 9; per mode, in
  order: wheel clockwise, counter-clockwise, press. The mode button sends no event. Every wheel click is an `initial_press` of its direction
  button, arriving at once; the dimmer's radio sends quick clicks in a burst (several within milliseconds), and its `multi_press_complete`
  count is unreliable, so only `initial_press` is used for the wheel. The wheel press uses Fast Matter switch's `fast_event_type` (needs Fast
  Matter switch 0.5.0 or later).
- Tests: `uv venv --python 3.14 .venv && uv pip install --python .venv/bin/python pytest-homeassistant-custom-component==0.13.375 ruff`, then
  `.venv/bin/python -m pytest` and `.venv/bin/ruff check . && .venv/bin/ruff format --check .`. Nothing is mocked inside the integration;
  the light service is recorded.
- No dependency beyond Home Assistant. Licence GPL-3.0-or-later; Python files start with the SPDX line. Private and local until the owner
  says to publish.
