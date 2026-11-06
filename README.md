# IKEA BILRESA dimmer

A Home Assistant custom integration for the IKEA BILRESA dimmer (two buttons and a wheel) that reports the wheel at the first click and
dims lights smoothly. It builds on [Fast Matter switch](https://github.com/bora-yarkin/fast-matter-switch), which reports Matter button
presses the moment the dimmer sends them instead of after the multi-press window.

Nothing is set up in the integration. It gives you **entities and an action**; what each mode of the dimmer controls, and by how much,
is an ordinary automation.

## Entities

For each BILRESA dimmer in Matter (a Matter device with nine buttons) there are three **event entities**, one for each of the dimmer's
modes (the mode button switches between them), named after the dimmer: `event.<dimmer>_mode_1`, `_mode_2`, `_mode_3`. They report:

| Event type | When | Attributes |
|---|---|---|
| `clockwise` | the wheel was turned clockwise | `steps`: positive, 1 or more |
| `counter_clockwise` | the wheel was turned counter-clockwise | `steps`: negative |
| `press` | the wheel was pressed | |
| `double_press` | the wheel was double-pressed | |
| `long_press` | the wheel was held | |

- A wheel event is sent for every click at once. `steps` counts the clicks that arrived together (the dimmer's radio sends quick clicks in
  a burst), and counts later clicks of a turn for more: the first three clicks of a turn are one step each, the next five two each, and
  after that three each. A pause of more than a second, or turning the other way, starts a new turn.
- The mode button sends no message; the mode is known from which buttons fire.
- Wheel presses follow Fast Matter switch's rule (the second touch of a double press is not a `press`).

## The action `bilresa_dimmer.adjust_light`

Moves lights by a number of steps, with a fade.

| Field | |
|---|---|
| Target | the lights |
| `attribute` | `brightness`, or `color_temp` (lights in colour temperature mode only) |
| `steps` | how many steps, negative for dimmer or warmer |
| `percent` | the size of one step, in percent of the light's range (default 5) |
| `transition` | the fade in seconds (default 0.3) |

Brightness never goes below 1 % (the wheel does not switch a light off), and a light that is off is switched on by a positive change and
left alone by a negative one. Colour temperature moves inside the light's own range, clockwise towards cooler. A light that cannot be
dimmed, or is unavailable, is left alone. While a light is still fading, the next call builds on what was asked for, so the light keeps up
with a fast turn.

## Example: mode 1 dims and toggles the desk light, mode 2 sets its colour temperature

```yaml
alias: Dimmer mode 1
triggers:
  - trigger: event.received
    target: {entity_id: event.living_room_bilresa_dimmer_mode_1}
    options: {event_type: [clockwise, counter_clockwise]}
    id: turn
  - trigger: event.received
    target: {entity_id: event.living_room_bilresa_dimmer_mode_1}
    options: {event_type: [press]}
    id: press
actions:
  - choose:
      - conditions: {condition: trigger, id: turn}
        sequence:
          - action: bilresa_dimmer.adjust_light
            target: {entity_id: light.desk_light}
            data:
              attribute: brightness
              steps: "{{ trigger.to_state.attributes.steps }}"
              percent: 5
      - conditions: {condition: trigger, id: press}
        sequence:
          - action: light.toggle
            target: {entity_id: light.desk_light}
mode: queued
```

Use `attribute: color_temp` for a mode that sets the temperature. A mode with no automation does nothing.

## Requirements

- Home Assistant 2026.10 or later with the Matter integration, the BILRESA dimmer added to it, and **Fast Matter switch 0.5.0 or later**
  set up.

## Set up

Install and restart as usual (see the Marketplace notes in Fast Matter switch's README), then **Settings, Devices & services, Add
integration, IKEA BILRESA dimmer** and confirm. There is nothing to configure.

## How the buttons are laid out

The nine Matter buttons are, for each mode in order, wheel clockwise, wheel counter-clockwise and wheel press: buttons 1 to 3 for mode 1,
4 to 6 for mode 2, 7 to 9 for mode 3. The dimmer sends one `initial_press` per wheel click, at once; its own click count comes later and
is often wrong, so it is not used.
