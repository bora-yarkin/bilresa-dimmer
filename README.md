# IKEA BILRESA dimmer

A Home Assistant custom integration that makes the IKEA BILRESA dimmer (two buttons and a wheel) dim lights smoothly, at the first
click of the wheel. It builds on [Fast Matter switch](https://github.com/bora-yarkin/fast-matter-switch), which reports Matter button
presses the moment the dimmer sends them instead of after the multi-press window.

## What it does

The dimmer has a mode button that switches between three modes. Each mode has its own lights:

| Control | Does |
|---|---|
| Turn the wheel clockwise | Brightens the lights of the current mode |
| Turn the wheel counter-clockwise | Dims them (never to off; the wheel press switches off) |
| Press the wheel | Switches the lights of the current mode on or off |

- **Every click counts at once.** A click moves the brightness by a step with a 0.3 second fade. Clicks the dimmer sends together are
  applied as one change.
- **Longer turns move faster.** The first three clicks of a turn move 5 %, the next five 10 %, and after that 15 % each. A pause of
  more than a second, or turning the other way, starts again with 5 %.
- **A light that is off** is switched on by the first clockwise click (at 5 %); counter-clockwise leaves it off.
- A mode with no lights does nothing. Double and long presses of the wheel are not used by this integration; use them in an automation
  through Fast Matter switch's event entities.

## Requirements

- Home Assistant 2026.10 or later with the Matter integration, the BILRESA dimmer added to it (it appears as one device with nine buttons),
  and **Fast Matter switch 0.5.0 or later** set up.

## Set up

1. Install and restart as usual (see the Marketplace notes in Fast Matter switch's README; this repository is added the same way).
2. **Settings, Devices & services, Add integration, IKEA BILRESA dimmer.** Pick the dimmer, then the lights of each mode (mode 1 is
   required). Change them later with **Configure** on the integration.

## How the buttons are laid out

The nine Matter buttons are, for each mode in order, counter-clockwise, clockwise and wheel press: buttons 1 to 3 for mode 1, 4 to 6 for
mode 2, 7 to 9 for mode 3. The dimmer sends no message when the mode changes; the mode is known from which buttons fire.
