# D-032: scope exempts the kit-owned specs surfaces unconditionally

`audit.py scope` flags every changed path a contract doc does not
name. The shared-registry files `specs/INDEX.md` and
`specs/CONSTITUTION.md` were "shared" — but still flagged unless a
contract doc named them — so a delivery whose repo scaffolded its
first spec during intake (scaffold.sh registers INDEX, creates
CONSTITUTION) carried standing UNMENTIONED rows the fixer could only
silence with a D-### naming files no implementer wrote. Recorded live
in the 2026-10-27 eval pass (E6 transcript): scope flagged
scaffold.sh's own repo-level files on a green delivery.

**Decision**: INDEX and CONSTITUTION are kit-owned registry surfaces,
maintained mechanically by scaffold.sh and archive.sh, never by an
implementer — expected delivery surface, exempt from the
named-in-docs requirement exactly like the spec's own tree.
`specs/context/` keeps the named-in-docs rule (it is authoring-time
content; a post-approval change there is worth a look), and every
other specs/ path outside the spec's own tree is still scope creep.
