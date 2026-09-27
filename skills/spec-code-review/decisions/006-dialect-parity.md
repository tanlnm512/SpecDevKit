# D-006: Two hand-maintained workflow dialects, pinned by parity tests

`workflows/spec-code-review.dwf.ts` (zcode: persistent typed agents,
`world.run`) and `workflows/spec-code-review.js` (Claude Code: one-shot
agents, shell only through probe agents, schema-validated results) are
hand-maintained masters of one protocol. The protocol spine — phases,
panel, tunables, ask anchors, report contract — is pinned identical in
both by `tests/test_workflow_copies.py`, plus a const-reassignment
scanner (the TS2588 class that shipped broken in 0.7.0 while every
text-anchor test stayed green).

**Why**: the two runtimes expose different primitives (no fs/shell in
the claude script; no user-installable agent types on zcode), so the
seams differ by necessity — but the protocol must not. Parity anchors
make "edited one master, forgot the other" a test failure instead of a
user-visible divergence. Text anchors do not execute code; the scanner
covers the crash-class gap.

**Cost if wrong**: dialect drift means the same review means different
things on different harnesses, and every fix must be rediscovered per
dialect.
