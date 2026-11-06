# IKEA BILRESA dimmer: project instructions

- Domain `bilresa_dimmer`. A single config entry with no settings (`config_flow.py`). `events.py`: `DimmerEvents` listens to Fast Matter
  switch's `fast_matter_switch_event` bus events, adds up the steps of wheel clicks that arrive within 50 ms and dispatches them; `event.py`:
  three event entities per dimmer (a Matter device with exactly nine Matter event entities), `clockwise` / `counter_clockwise` with a
  `steps` attribute, and the wheel press types; `dimming.py`: pure step logic (`Turn`); `lights.py` and `__init__.py`: the
  `bilresa_dimmer.adjust_light` action. What a mode controls is decided in the user's automations, never in the integration (owner's decision,
  2026-11-06).
- Button layout and counting, from captures of the real dimmer on 2026-11-06 and the owner's tests: buttons 1 to 9 are Matter endpoints 1 to 9;
  per mode, in order: wheel clockwise, counter-clockwise, press. The mode button sends no event. A slow turn sends one `initial_press` per click.
  A fast turn sends an `initial_press` only about every 0.5 s (18 clicks showed as 4 presses) and the real clicks are in `presses` of the
  `multi_press_ongoing` events (cumulative for the sequence: 8, 14, 18) and the closing `multi_press_complete`; `dimming.ClickCounter` turns
  both into new clicks. A sequence seems to stop at 18 clicks and the next starts at once. The dimmer's radio also sends events in bursts
  (several within milliseconds). The wheel press uses Fast Matter switch's `fast_event_type` (needs Fast Matter switch 0.5.0 or later).
- Tests: `uv venv --python 3.14 .venv && uv pip install --python .venv/bin/python pytest-homeassistant-custom-component==0.13.375 ruff`, then
  `.venv/bin/python -m pytest` and `.venv/bin/ruff check . && .venv/bin/ruff format --check .`. Nothing is mocked inside the integration;
  the light service is recorded.
- No dependency beyond Home Assistant. Licence GPL-3.0-or-later; Python files start with the SPDX line. Private and local until the owner
  says to publish.
