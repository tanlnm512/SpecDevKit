# D-010: Sharded project coverage — every file, in parts

Project mode reviews every tracked source file. A target too large for
one reviewer's turn is sharded: contiguous runs of the path-sorted
list — directories stay together — closed at SHARD_TARGET_BYTES
(240 000) or SHARD_MAX_FILES (32), with a too-small trailing run
merged into the previous part. Every lens reads every part; the lens's
findings are the concatenation before triage, and triage/cross-lens
merge/confirmation run unchanged on the merged set. This replaces the
0.4.0 cap of the 30 largest files.

**Why**: the cap existed so one reviewer's turn could actually cover
its list — but "review the whole codebase" then produced "covered 30
of 441" with a notCovered apology, on exactly the request the mode
advertises. Sharding keeps each turn readable (a part ≈ 240 KB ≈ the
old cap's load) while making coverage complete: directory-coherent
contiguous runs give a reviewer sibling files as shared context, and
byte-balancing stops one 111 KB file from pairing with 31 more into an
unreadable part. Determinism (sort, then accumulate) means a rerun
re-derives the same parts.

**Cost if wrong**: full coverage is not free — a 441-file repo reads
as 18 parts × 3 lenses = 54 reviewer sessions, an order more than the
capped three. That is the honest price of "audit everything"; the cap
was cheaper and quietly reviewed 7% of the target. The knob for cost
is `paths` (narrow the target), not silently dropping files; the
tunables (SHARD_TARGET_BYTES / SHARD_MAX_FILES) live in control flow
only, never in ask text.
