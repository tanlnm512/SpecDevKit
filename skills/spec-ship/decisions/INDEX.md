# Decision index — spec-ship

ADRs are append-only. New decisions continue from the highest number
(D-007 is the latest).

| ID | File | Decides |
|----|------|---------|
| D-001 | `001-outward-work-on-the-users-yes.md` | ship does push, PR, and replies on the user's yes — extends spec-build D-014, gates stay human |
| D-002 | `002-shipped-record-beside-delivered.md` | where `Shipped: PR <url>` is recorded, per tier |
| D-003 | `003-evidence-out-fixes-elsewhere.md` | ship never fixes code; evidence routes to `/spec-build`; spec-less branches refused |
| D-004 | `004-tests-pin-the-run-contract.md` | `tests/test_ship.py` pins the run contract: stage table, refusals, record/evidence shapes, and the read-only-remote guarantee |
| D-005 | `005-ci-triage-red-checks-classed.md` | every red check is classed code/infrastructure/unknown from run step evidence; `ci-rerun` opens no fix round; the rerun command is printed, never run |
| D-006 | `006-owner-rulings-on-review-threads.md` | the owner's thread labels are recorded by `rule` and read back by `comments`; a ruled thread is not reclassified |
| D-007 | `007-ruled-proofs-in-the-pr-body.md` | `pr-body` reads the delivery block (the note only as fallback) and lists each ruled environment-blocked proof as `Owner to test after merge: TC-### — <ruling>` — never shown as passed |
