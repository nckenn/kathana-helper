# Smoke test checklist (manual)

Run this checklist after significant refactors.

## Setup

- Install deps: `pip install -r requirements.txt -r requirements-dev.txt`
- Start: `python main.py`

## Core flows

- **License flow**: Invalid license shows activation dialog; valid license opens main UI.
- **Connect window**: Connect/disconnect works; window change resets connection.
- **Calibration**: HP/MP bars + skill area + system message area can be calibrated; bot start is disabled until calibrated.
- **Start/stop**: Start/stop bot works repeatedly; no lingering clicks/keys after stop.

## Combat

- **Auto Attack enabled**: Targets mobs, attacks, loots after kill, retargets.
- **Mob filter**: When enabled + target list set, only attacks matching mobs; avoid list is honored.
- **Skill sequence**: Skills fire in order when enemy found; sequence resets on enemy lost/death.

## Assist Mode

- **Assist key**: With Assist Mode enabled and assist hotkey configured, assist key is pressed on interval.
- **No auto-targeting**: Bot does not attempt to auto-target when Assist Mode is enabled.

## Buffs

- **Buff detection**: Buffs only activate when missing; active buffs are detected from the buff strip above system message area.

## Pots

- **HP pots**: Triggers at threshold(s) with correct cooldown behavior.
- **MP pots**: Triggers below threshold with correct cooldown behavior.

## Auto repair

- **Warning detection**: Light-green warning text triggers repair key press.
- **Cooldown**: Respects repair cooldown; doesn’t spam key.

## Performance

- **CPU usage**: Compare Task Manager CPU with bot idle vs active combat.
- **No debug disk I/O**: Debug images are not written unless debug saving is explicitly enabled.

