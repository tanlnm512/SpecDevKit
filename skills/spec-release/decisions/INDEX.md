# Decision index — spec-release

ADRs are append-only; new decisions continue from the highest number.

| ID | File | Decides |
|----|------|---------|
| D-001 | `001-the-release-node.md` | the release phase is its own skill, starting from merged delivered work; never deploys |
| D-002 | `002-released-record-placement.md` | `Released:` lives in the status holder, in a record commit after the tag |
| D-003 | `003-two-yeses-and-confirm-echo.md` | the local cut and the publish are separate yeses; `--confirm <tag>` re-checks the gate |
| D-004 | `004-facts-first-notes.md` | the script writes the notes from facts; the release manager edits wording only |
| D-005 | `005-bump-rules.md` | SemVer bump from work types and breaking markers; every version source reported |
