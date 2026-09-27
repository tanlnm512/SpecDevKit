# D-007: Precision over recall — no findings caps, curated detectors

Findings are severity-ordered and never truncated ("top 5" caps
suppress real defects by fiat — rejected). The gate's secret family
scans a curated set of token SHAPES with no legitimate diff presence
(AWS/GitHub/GitLab/Stripe/Slack/Google/npm/Anthropic keys, private-key
headers) over added lines and untracked files only — diff mode only,
because project mode would false-positive on fixture files with fake
keys. The security lens owns whole-project secret reading, where
context can tell a fixture from a leak.

**Why**: the 2026 trust metric for AI reviewers is precision; recall
chases produce the noise that gets reviewers muted. Every deterministic
family is held to the same bar: prose about keys never trips the secret
scan, style never becomes a finding, speculation is dropped at triage.

**Cost if wrong**: a findings cap hides the sixth real defect; a
greedy secret scanner fails the gate on every documentation example
and gets switched off — the worst outcome of all.
