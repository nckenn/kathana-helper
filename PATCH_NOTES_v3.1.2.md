# Kathana Helper v3.1.2 — Patch Notes

**Release:** v3.1.2  
**Previous:** v3.1.1

---

## Upgrade Note — read this first

**If you downloaded v3.1.1, replace it.** That build did not start: it closed
immediately, with no window and no error message. This release fixes that, along
with two other faults that only ever showed up in the packaged download.

Nothing about your settings changed. Your profile, regions, mob templates, skill
sequence and buffs all carry over untouched — download the new `.exe`, put it
where the old one was, and carry on.

---

## Bug Fixes

- **v3.1.1 would not launch.** The window picker registered its change handler
  with the old `trace('w', ...)` form, which asks Tcl to run `trace variable` —
  a command removed in Tcl 8.7. The Tcl bundled into the build rejected it and
  the app died while building its own window, before anything appeared on
  screen. Running from source was unaffected, which is why it reached a release.

- **The skill picker was empty.** Every job tab — Abikara, Samabat, Banar,
  Satya, Nakayuda, Vidya, Druka, Karya — opened with no icons in it, so no buff
  or skill-sequence slot could be filled from the picker. Splitting `gui.py` into
  modules in v3.1.1 moved the picker two folders deeper, and it was still looking
  for the `jobs` folder next to its own file. It now resolves from the
  application root, and all 194 skill icons load again.

- **The window icon was missing.** The app looked for `icon.ico` beside the
  `.exe` and deliberately ignored the copy inside the build, but nothing ever
  places one there — so the title bar and Alt-Tab fell back to a generic icon.
  It now uses the bundled copy. Dropping your own `icon.ico` next to the `.exe`
  still overrides it, without a rebuild.

---

## Notes

- Windowed or borderless windowed mode works best for alt-tab and background capture; exclusive fullscreen may not capture correctly.
- Re-learn mob templates if you change the enemy name scan region.
- When moving installs, copy both your profile JSON files and the `mob_templates/` folder.
- Windows may warn about an unrecognised publisher when running the download — the build is unsigned. Choose **More info → Run anyway**.
