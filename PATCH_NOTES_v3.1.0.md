# Kathana Helper v3.1.0 — Patch Notes

**Release:** v3.1.0  
**Previous:** v3.0.0

---

## New Features

- **Visual Region Editor** — capture the game window and draw, drag, and resize regions on a canvas (replaces in-game fullscreen picking).
- **Regions toolbar button** — opens the editor from the main window; shows **✓ Regions** when HP + MP are set (replaces the old Regions tab).
- **Settings profiles** — **Save**, **Save As…**, and **Load…** for JSON profile files; active profile name shown in the toolbar.
- **Per-profile mob templates** — each profile stores learned mobs in its own folder (`mob_templates/<profile_name>/`).
- **Region editor controls** — zoom (+/−, Fit, 100%, Ctrl+wheel), arrow-key nudging (Shift for faster steps), Delete to clear a region.
- **Bot-start preflight** — warns if required regions or mob filter setup is missing before Start.
- **Connect + Refresh** — Connect moved to the window row and refreshes the window list before connecting.

---

## Improvements

- **Capture performance** — HP/MP, repair, and mob filter share a frame cache; union-region capture when the game is focused.
- **Combat stability** — mob filter uses 2-of-N miss tolerance during combat to avoid dropping targets on a single bad read.
- **Mob filter performance** — precomputed template signatures and separate combat vs idle scan intervals.
- **Auto-pots** — skips pot use when HP/MP reads are stale after repeated capture failures.
- **Buff activation** — requires 2 consecutive “not active” checks, 4s press cooldown, and 4s post-cast grace before re-pressing.
- **CV tuning** — buff/skill thresholds and match margins centralized in config and saved with profiles.
- **Region editor sidebar** — compact rows, color swatches, full-row click to select.
- **UI layout** — window row: Connect | Refresh; bot bar: Start | Regions.
- **Versioning** — single `APP_VERSION` in config; title bar and PyInstaller build name stay in sync.
- **Build** — `kathana_helper.spec` bundles `ui.region_editor`, `match_utils`, and related modules.
- **Tests** — expanded suite (70 tests) for capture, combat, buffs, profiles, and regions.
- **Dependencies** — removed unused `scikit-image` and stale EasyOCR references.

---

## Bug Fixes

- **Alt-tab / background capture** — fixed wrong HP/MP and combat reads when another window covers the game; uses PrintWindow instead of screen grab when the game is not focused.
- **Frame cache on focus change** — cache invalidates when switching between foreground and background so stale frames are not reused.
- **Buff hotkey spam** — fixed repeated buff presses from bad captures, short cooldown, and cast delay not being accounted for.
- **Buff strip crop** — falls back to direct region capture when the cached crop is empty or invalid.
- **Mob templates across profiles** — fixed learned mobs from one profile appearing in another after Load; orphan recovery is now scoped per profile.
- **Legacy mob migration** — templates in the old flat `mob_templates/` folder are copied into the active profile folder on load.
- **Save As profiles** — mob template images are copied into the new profile folder when saving under a new name.
- **PyInstaller build** — fixed spec file failing to import `config` for version (`SPECPATH` path fix).
- **Region editor list** — fixed oversized sidebar rows and hard-to-click region selection.

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
