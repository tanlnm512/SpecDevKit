# D-073: the tester's blindness is guarded where the harness names the caller

The qa node's tester writes test.md from spec.md alone, beside tech and
plan; it never reads tech-spec.md, plan.md or task.md. That blindness
is a rule in the brief and a property of the payload the tester is
spawned with — nothing mechanical stops a tester spawn that goes
looking. The hardening plan's item 2.2 asks for the mechanical stop: a
hook denying the tester `Read` on those three files.

The approval guard (D-072) already runs before the tools its
registration matches, on a harness where the owner registered it, and
a hook payload may carry the caller's identity. Whether any harness
puts one there is not established by this repository.

**Decision**:

1. **P4 — the tester is denied a read of the implementation docs, best
   effort.** A `Read`, `NotebookRead` or `view` of
   `specs/<name>/{tech-spec.md,plan.md,task.md}` is denied when the
   caller identity in the hook payload names the tester (`spec-tester`,
   `tester` — as a whole word, in `agent_type`, `subagent_type`,
   `agent_id` or `agent_name`), with a reason line naming the rule.
2. **With no caller identity, P4 allows and says nothing.** The guard
   never denies a read on a guess. The rule's teeth stay where they
   were — the spawn payload and the brief — on every harness that names
   no caller.
3. **The guard fails open here as everywhere.** Unreadable input or an
   internal error allows; the reason line names the rule and the
   remedy, since spec.md is the tester's whole input.
4. **One guard, one registration.** P4 rides the same
   `spec-kit-guard.py` and the same `REGISTER.md` as P1–P3 — `Read` is
   in the registration's matcher — so the tester half of item 2.2
   costs no second hook.

**Consequences**: where the owner registered the guard and the harness
names the caller, a tester spawn that reaches for tech-spec.md is
stopped before it reads, and told why; it costs nothing where neither
holds. The cost if wrong is the same silence as D-072's — a harness
that names the caller under a field the guard does not read runs P4 as
a no-op — and its opposite is empty: an identity that names a tester
forbids no read the tester needs, since spec.md and the test.md it
writes are that role's whole input.
