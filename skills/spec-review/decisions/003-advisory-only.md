# D-003: The panel advises; the human decides

The run ends in a recommendation (merge / fix-first / human — criteria
canonical in `gates/recommendation.md`). The panel never blocks a
merge by itself, never commits, and routes judgment calls to `human`.
Fixes stay uncommitted in the working tree; the commit decision and
message are the user's.

**Why**: human ownership of the final approval is the stable principle
across every credible 2026 practice. The only blocking gate is the
repo's own mechanical checks (D-001) — deliberately not an AI verdict,
because an AI hard gate fails loudly on the reader's behalf far more
often than on a real defect. (A phased-rollout proposal suggested an
AI-owned hard gate and hard findings caps; both were rejected here.)

**Cost if wrong**: an AI gate that blocks is a denial-of-service
primitive against the author, and trust collapses the first time it
blocks wrongly.
