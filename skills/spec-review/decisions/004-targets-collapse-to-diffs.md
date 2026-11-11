# D-004: branch and pr are merge-base diffs, not new review modes

`target: branch` and `target: pr` resolve to a base (merge-base with
the base branch / the PR's base commit — GitHub's own PR-diff
semantics) and then run the unmodified diff-mode machinery: same asks,
same gate, same confirmation, same fix loop. Only the resolution step
is new code, and it runs before anything else.

**Why**: one review path serves all four targets; every target-specific
branch in the panel would be a parity fork between the two workflow
dialects. The pr head must be checked out because the panel reads the
working tree — hence the unconditional dirty-tree refusal (a dirty tree
misattributes uncommitted work to the PR whether or not the head
already matches).

**Cost if wrong**: per-target panel variants drift from each other and
from the tests; a conditional dirty check (checkout-path only) was
exactly the 0.7.0-era defect class the panel review caught.
