# D-003: The artifact lives at brainstorms/<name>.md, never under specs/

The design specification is written to `brainstorms/<name>.md` at
the repository root (a user-named path wins). The tempting
placement — `specs/<name>/brainstorm.md`, so the brainstorm
travels with the eventual spec docset — is refused for two
mechanical reasons in spec-to-prod, both verified in its code:

1. `scaffold.sh` refuses to run when `specs/<name>/` already
   exists. A brainstorm artifact written pre-scaffold would block
   the very `/spec` run it was meant to feed.
2. `check.py`'s `other_specs_exist()` counts any directory under
   `specs/` other than `context/` and `archive/` as another spec.
   A stray `specs/brainstorms/` would flip the repo from
   first-spec to second-spec early, tripping the
   constitution-required gate ahead of schedule.

A deeper placement would mean changing spec-to-prod (a scaffold
tolerance, an exclusion entry) — coupling two skills that the
repo keeps independently installable, to save one directory.
Pre-spec material is also lower ceremony by nature: most
brainstorms die before any spec exists, and a graveyard of
scaffold-shaped dirs for ideas that never graduated is exactly
the noise `specs/` should not accumulate.

**Why**: the toolkit's front gate is mechanical — scaffold's
refuse-to-overwrite and check.py's spec-dir census — and zero
coupling keeps this skill installable alone.

**Cost if wrong**: two adjacent top-level doc roots (`specs/` and
`brainstorms/`). Accepted: the separation is honest — graduated
work vs. pre-graduation exploration — and the handoff message
names the `/spec <name>` step that moves an idea across.
