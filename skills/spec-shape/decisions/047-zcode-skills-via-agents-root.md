# D-047: zcode serves skills through the ~/.agents compatibility root

sync deployed every skill twice for zcode: once to the native
`~/.zcode/skills/` and once to `~/.agents/skills/` — and zcode scans
BOTH roots, so its skill list showed two entries per skill (ten
spec-* listings for five skills; observed 2026-10-27 after the
machine-wide sweep confirmed no other spec-* strays existed).

**Decision**: `~/.zcode/skills/` leaves `SKILLS_ROOTS` — zcode
discovers the kit through the `~/.agents/skills` compatibility root
it already scans, the same copy opencode/droid/kilo read (claude
keeps its own native root; omp its priority-100 root). Commands stay
native in `~/.zcode/commands/` — commands were never duplicated.
One-time machine step (recorded for any machine that ran the old
sync): delete the kit's skill dirs and their ledger from
`~/.zcode/skills/`; sync no longer manages or cleans that root.
