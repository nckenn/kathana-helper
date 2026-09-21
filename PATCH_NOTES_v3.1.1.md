# Kathana Helper v3.1.1 — Patch Notes

**Release:** v3.1.1  
**Previous:** v3.1.0

---

## Upgrade Note — read this first

**Skill Sequence now waits instead of skipping.** In v3.1.0 the sequence always
skipped a skill that was on cooldown, so a strict 1→2→3 opener was impossible.
It now casts in slot order and **waits** for a skill that is on cooldown, unless
that skill has **Skip if on cooldown** ticked.

If your rotation used to keep moving and now seems to pause, open the **Skill
Sequence** tab and tick **Skip if on cooldown** (the right-hand checkbox) on the
skills you want passed over. Ticking it on every slot reproduces the old
behaviour exactly.

Your existing per-skill settings are preserved — the upgrade does not change
them, and it logs a warning pointing at these checkboxes when it loads a profile
from before this release.

---

## New Features

- **Strict skill rotation** — skills cast in slot order 1→2→3… then back to 1, and an earlier skill is never cast after a later one.
- **Skip if on cooldown (per skill)** — a second checkbox on each Skill Sequence slot decides whether the rotation waits for that skill or moves past it. Replaces the old global Cast mode selector.
- **Settings profiles are versioned** — profiles now record a schema version, so an older profile can be recognised and migrated instead of silently picking up defaults.

---

## Improvements

- **Compact toolbar** — the window selector, status strip and bot controls were three stacked cards taking about a third of the window. They are now one toolbar, giving roughly 150px back to every tab.
- **Buttons show what matters** — four consistent roles: Start (green), Connect (blue), everything else clickable (grey), and stored values like hotkeys as outlined chips. A saved hotkey no longer looks like a button you should press.
- **Readable at any window size** — the toolbar status line no longer clips at the default 720px width, long window titles are shortened rather than stretching the layout, and the window has a sensible minimum size.
- **Instructions out of the way** — the "How to use" blocks on Skill Sequence and Buffs are collapsed by default, so the controls are the first thing on the tab. Click the header to read them.
- **Two fonts, each doing its job** — labels and prose use a proportional face; hotkeys, percentages, filenames and coordinates stay monospace so they line up and read character by character.
- **Status tab leads with live data** — HP, MP and enemy HP are at the top; License Info is collapsed below, since it is read once.
- **Logging** — the bot-loop modules log through a single logger with timestamps and a module tag, which makes a saved log useful when something goes wrong.
- **Tests** — 110 → 189, now run automatically on every push.

---

## Bug Fixes

- **Saving a profile can no longer corrupt it** — saves are atomic. A crash, a full disk, or the process being killed mid-save used to leave a truncated file, losing every region calibration and every skill and buff binding. The previous profile now survives.
- **The bot no longer stops silently** — an unhandled error in any subsystem used to kill the bot thread while the window still showed "Running" and every control still worked. Each loop iteration is now guarded: the failure is logged with the exact call that failed, and the bot keeps going. If the thread does die, the window says so instead of pretending.
- **Minimise works again** — clicking minimise opened the overlay but left the main window on screen.
- **Calibration errors show the error** — a failed calibration raised a second error while trying to report the first, so the real message was lost. Same fix in the Region Editor's capture-error path.
- **Calibration log line** — the "minimum threshold" message referenced a value that did not exist and would crash when a chat-bar match failed.
- **Skill Sequence stall** — a ready skill that never casts (not enough resources, say) no longer holds up the rotation; it is passed after a few attempts.

---

## Under the Hood

Nothing user-visible, but it is why the fixes above were findable:

- `gui.py` was 5,824 lines in one class. It is now about 3,200, with the license, region pickers, mob filter, skill selector, mini overlay and debug window in their own modules.
- The five region pickers were 181-line copies of each other differing in about 20 lines; they now share one implementation (1,068 → 367 lines).
- A check runs over every module for names that are used but never defined — the class of bug that broke minimise, and which import alone does not catch. It found three more latent ones, all on error paths.
- Builds are produced by CI from a clean checkout and published automatically.

---

## Quick Start

1. **Connect** → select game window.
2. **Regions** → set HP, MP, and other areas in the editor.
3. **Learn** mobs (Mob Filter tab) if using whitelist filtering.
4. **Save** your profile.
5. **Start** the bot.

---

## Notes

- Windowed or borderless windowed mode works best for alt-tab and background capture; exclusive fullscreen may not capture correctly.
- Re-learn mob templates if you change the enemy name scan region.
- When moving installs, copy both your profile JSON files and the `mob_templates/` folder.
- Windows may warn about an unrecognised publisher when running the download — the build is unsigned. Choose **More info → Run anyway**.
