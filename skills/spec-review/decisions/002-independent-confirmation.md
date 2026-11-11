# D-002: Every kept finding is confirmed by someone who did not write it

After triage, each kept finding is re-derived from the code alone by a
separate confirmer: verified or unconfirmed, one sentence of what was
seen. Failed confirmation never drops a finding — it ships labelled
`unconfirmed`. Confirmation is intent-blind: the confirmer never sees
the stated-intent channel.

**Why**: precision, not recall, is what makes an AI reviewer trustworthy
(the industry's 2026 lesson — false positives are the reason developers
mute AI reviewers). The reviewer who wrote a finding is the worst
person to re-check it; independence is the only cheap false-positive
filter that does not also suppress real defects.

**Cost if wrong**: self-confirmed findings ship the reviewer's
misreadings as verdicts; a confirmation step that could see intent
becomes a rubber stamp for convenient findings.
