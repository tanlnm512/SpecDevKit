# D-081: the approver list is read from one trusted location — the machine list, or in CI the remote default branch — never from the working tree

An approval is a signature (D-071) made by a key in the repo's approver
list `specs/.approvers`, and freeze.py found that list by walking up
from the spec dir to the nearest `specs/.approvers`. So the list lived
where every write-capable agent writes: a nested
`specs/<name>/specs/.approvers` holding the agent's own key shadowed
the root list — approve signed with it and verify passed — and the
CODEOWNERS rule D-071 recommends covers only the two root patterns. An
edited root list defeats the signature the same way.

**Decision** (freeze.py is canonical; spec-build adopts it in its
D-073):

1. **One resolver feeds `--approve` and `--verify`, and nothing else
   reads an approver list.** `_approvers` yields the list as the file
   ssh-keygen reads, or the reason none can be trusted:
   - the machine list `~/.config/spec-dev-kit/approvers` — wherever it
     exists, in every mode, it is the authority and the workspace copy
     is not consulted;
   - else, when the `CI` variable is set to a non-empty value, the list
     as it stands on the remote default branch —
     `git -C <repo> show <remote-default>:specs/.approvers`, copied to
     a private temporary file for the life of the check.
     `<remote-default>` is the target of `refs/remotes/origin/HEAD`,
     else `origin/main`, else `origin/master`, always read by its full
     ref — git resolves a tag or a branch of the same short name first,
     and a session can make either. No such ref, or no such file on it:
     refuse, naming which is missing. freeze.py never runs `git fetch`
     — verify runs inside a PreToolUse hook and must not touch the
     network;
   - else (a local run with no machine list) refuse, naming the file to
     create.
2. **The workspace copy is never an authority.** `specs/.approvers` in
   the working tree is only what CI commits and what the owner reviews.
   A local run that holds nothing but a workspace list verifies nothing
   and signs nothing.
3. **A nested list is refused by name.** The workspace root is git's
   toplevel for the spec dir, else the `--repo` root. When a workspace
   list exists it must sit at exactly `<repo-root>/specs/.approvers`;
   verify — and approve — refuse while any other file named
   `.approvers` exists anywhere under `<repo-root>/specs/`, whatever it
   holds and whichever source the list came from, and name the file.
4. **Every refusal states where the list really lives.** No list, no
   remote default branch, no list on it, a signer outside it: each names
   the machine file, the remote ref, and the form of a line.
5. **D-071 paragraphs 1, 4 and 5 are amended.** The list is no longer
   "the repo's", and a CODEOWNERS rule on `specs/.approvers` no longer
   guards it: a local run's trust root is a file the workspace cannot
   write, and CI's is a ref only a push moves. The key's protection — a
   passphrase or hardware — is unchanged and still only recommended.

**Consequences**: an agent that can write anywhere in the workspace,
nested paths no CODEOWNERS rule names included, can no longer make its
own key an approver on a machine with the machine list or in CI. It
costs: one file per machine that approves or verifies, created by hand
before the first approval; a CI job whose checkout carries no remote
default branch as `origin/<branch>` fails closed until the checkout
fetches it or the job installs the machine list; and one walk of
`<repo-root>/specs/` on every verify. A clone whose remote default
branch is named otherwise and that has no `origin/HEAD` is refused by
name, never guessed at. The cost if wrong is D-071's: a passphrase-less
key in the agent's reach signs anything, and a machine list the agent's
shell can write to is as good as a workspace list was — the guard
(D-084) denies that write where it is registered, and nothing else
does.
