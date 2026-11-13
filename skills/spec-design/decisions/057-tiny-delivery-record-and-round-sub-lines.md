# D-057: the tiny tier's delivery record and fix-round sub-lines read where the contract puts them

Live eval runs (E7, E9) showed two shared-engine readers disagreeing
with spec-build's contract at `Tier: tiny`:

- The contract writes `Delivered: commit @ <C1>` into spec.md
  § Evidence. check.py and `audit.py dod` read it there; graph.py read
  the delivery record only inside § Tasks, so a delivered spec still
  read `tick-commit READY … delivery unproven` and archive stayed
  blocked.
- spec-build's SKILL.md says the fix-round sub-lines move freely at
  tiny tier, but the approval freeze's § Tasks normalization stripped
  only the markers, `done <date> —` lines and the `Delivered:` record,
  so `fix <n> — <digest>` under a task broke the freeze.

**Decision**:

1. **graph.py reads the whole spec.md for the record at tiny.** The
   plain and bold `Delivered: commit @ <sha>` forms count wherever
   they sit — § Evidence or § Tasks. The done citation names spec.md
   as the holder.
2. **The freeze treats round sub-lines as status.** `fix <n> — …` and
   `fixed <n> — …` lines in § Tasks are normalized away like the
   markers and `done` lines. An added, edited, or struck task still
   breaks the freeze.

**Consequences**: the master copies in `scripts/` (graph.py,
freeze.py) changed; replicas were refreshed by `tools/parity.py`. The
node table in SKILL.md is unchanged. An approved tiny spec carrying
round sub-lines hashes the same as before they were written.
