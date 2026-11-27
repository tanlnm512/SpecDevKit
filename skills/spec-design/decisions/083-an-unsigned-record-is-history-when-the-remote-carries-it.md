# D-083: an unsigned record is history only when the remote default branch carries it

D-071 grandfathered unsigned records: a delivered docset whose record a
commit in the repo's ancestry — the delivery commit or HEAD — holds
byte for byte still verifies, so specs approved before signatures
existed keep shipping. But a commit is something a session makes: add a
`Delivered:` line, hand-write a record with the review trio, and
`git commit -a` — no path named, so the guard is blind — and the
unsigned record verified. The grandfather was the one way left to open
execute without a key.

**Decision** (freeze.py `_record_is_history` is canonical; the gate
consequence in spec-build's D-053 is unchanged):

1. **The grandfather resolves against the remote default branch**,
   resolved exactly as the approver list is (D-081): the target of
   `refs/remotes/origin/HEAD`, else `origin/main`, else `origin/master`,
   read by its full ref — a local tag or branch named `origin/main`
   resolves first when the short name is used, and a session can make
   either. An unsigned record is history only when the docset is
   delivered and that branch holds the record byte for byte,
   canonicalized, at the same path.
2. **HEAD and the claimed delivery sha prove nothing.** Neither is
   consulted. A local commit, a local branch, a `Delivered:` line: none
   of them makes an unsigned record an approval.
3. **With no remote default branch resolvable, it is not history.** An
   unsigned record is never an approval where nothing remote can vouch
   for it — a repo with no remote, a clone whose default branch is named
   otherwise and that has no `origin/HEAD`. Nothing is fetched; the
   refusal names the owner's re-approval.
4. **D-071 paragraph 6 is amended.** "A commit in this repo's ancestry
   carries it" becomes "the remote default branch carries it".

**Consequences**: the forgery needs the record on the default branch's
remote-tracking ref — which this decision reads locally, so one local
`git update-ref refs/remotes/origin/<branch>` moves it without any
outward action: a session that runs that command defeats the
grandfather, and the machine list does not shield it. The protection
holds against a session that does not also move git refs; closing it
would take a network read inside the gate or a guard on ref-moving git
commands, and neither is made here — the release notes carry the limit.
It costs: a delivered spec with an unsigned record verifies only where its
record has reached the remote default branch, so a repo that never had
a remote re-approves such specs once, by hand, before their next
execute, release or archive; and a checkout whose remote-tracking refs
are stale reads what it last fetched. The cost if wrong is that the
remote default branch is only as trustworthy as its push policy: a
session that can push to it can carry its own record — and can already
change anything else in the repo.
