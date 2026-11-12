# Decision index — spec-ship

ADRs are append-only. New decisions continue from the highest number
(D-004 is the latest).

| ID | File | Decides |
|----|------|---------|
| D-001 | `001-outward-work-on-the-users-yes.md` | ship does push, PR, and replies on the user's yes — extends spec-build D-014, gates stay human |
| D-002 | `002-shipped-record-beside-delivered.md` | where `Shipped: PR <url>` is recorded, per tier |
| D-003 | `003-evidence-out-fixes-elsewhere.md` | ship never fixes code; evidence routes to `/spec-build`; spec-less branches refused |
| D-004 | `004-tests-pin-the-run-contract.md` | `tests/test_ship.py` pins the run contract: stage table, refusals, record/evidence shapes, and the read-only-remote guarantee |
