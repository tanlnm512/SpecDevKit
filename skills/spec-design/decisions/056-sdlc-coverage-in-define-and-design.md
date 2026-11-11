# D-056: SDLC coverage in define and design

A gap review of the requirements and design phases against a full
SDLC found the docset silent or unenforced on ten points: the kind of
work a spec is, non-functional requirements (a fixture with no NFR
passed), threat modeling, interface and data design, UX, rollout,
sizing, onboarding a repo that already has conventions, the view
across specs, and who signed an approval.

**Decision** — each gap closes with the smallest tier-scaled thing: a
header, a template section that may say `none — <reason>`, one check,
one lens sentence, one auditor item. No new agent, no new docset file.
`Tier: tiny` gains one header line and nothing else.

1. **Work type.** `**Type**: feature | bugfix | hotfix | refactor |
   upgrade` on spec.md at both tiers; intent.md carries the same line.
   Absent reads feature; check.py refuses any other word. The lenses'
   bugfix deltas key on `bugfix | hotfix`; hotfix is the bugfix of the
   tiny tier. refactor and upgrade preserve behavior: user stories and
   ACs are optional, and check.py requires a test case carrying a
   `- **Preserves**: <existing behavior>` line (at tiny tier, a task
   `Accept:` command). Every payload names the work type.
2. **NFR triage is enforced.** A full-tier spec triages Security,
   Privacy, Performance, Reliability, Observability, and Accessibility:
   an NFR, or `not applicable: <reason>`. Families sharing a reason may
   share one line. intent.md's FR seeds carry one `NFR seeds` line the
   grill fills. Applicable NFRs already traced to a task and a TC.
3. **Threat model.** The tech-spec table stays trigger-conditional; the
   contract review BLOCKs a security-relevant trigger (auth, secrets,
   untrusted input, persistence of personal data) with no threat row.
   At tiny tier the same trigger means the spec outgrew its tier.
4. **Interfaces & data.** tech-spec.md `## Interfaces & data` — API
   shapes, data-model changes, migrations, compatibility — required at
   full tier.
5. **UX.** A user-facing UI adds `### UX` under § Interfaces & data
   (flows, empty/error/loading states, accessibility); the contract
   review WARNs when it is missing.
6. **Rollout.** plan.md § Delivery gains `### Rollout`, required at
   full tier; the contract review BLOCKs a rollout that contradicts
   the tech-spec's rollback column.
7. **Sizing.** A `Size` column (S/M/L) on plan milestones. Unchecked;
   never hours.
8. **Constitution lens.** The analyst gains a `constitution` lens that
   proposes articles from observed conventions, each cited to
   evidence, and writes nothing — D-055's rule stands: the user
   confirms every article. `graph.py --emit-spawns --repair
   constitution` emits it; it is not a graph node.
9. **Cross-spec view.** An optional `**Depends on**` header: an
   unknown name fails, an unapproved dependency warns, and so does an
   in-flight (approved or active) spec whose pending `Touches:`
   overlap this spec's, unless one of the pair depends on the other.
   `scripts/index.py` renders each spec's `specs/INDEX.md` line
   (`<status> · <type> · <tier>[ · depends on …]`) and is the line's
   one writer: scaffold.sh calls it, and check.py warns when the
   committed line differs from the render. It joins the parity closure.
10. **Sign-off.** `freeze.py --record --by "<name>"`, repeatable,
    writes `**Approved-by**` lines into approvals/approval.md.
    Optional.

**A frozen contract is not failed retroactively.** The coverage checks
of 1, 2, 4, and 6 FAIL a draft and only WARN once Status is approved
or later: repairing them edits a frozen file, which is a re-approval,
and a spec mid-execution must not go red because the checker grew.

**Consequences**: a full-tier draft authored before this decision
fails verify until it triages the six families and adds the two
sections — one line and two short sections for a small spec. An
INDEX.md line in the old `— draft (created <date>)` shape warns as
stale until `index.py --all specs` re-renders it; the status word
stays directly after the dash, so archive.sh's in-place repoint still
yields the rendered line. `n/a` is not a second spelling: the triage
literal stays `not applicable: <reason>`, the one check.py already
read. Left out on purpose: a UX agent, an estimates field, a
dependency graph renderer, a mechanical threat-trigger scan (the
trigger is a judgment — it is the auditor's), and required approvers.
