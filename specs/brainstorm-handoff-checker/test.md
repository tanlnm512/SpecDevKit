# Test Cases: brainstorm-handoff-checker

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-05
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

The operator surface under test is the handoff checker CLI: it takes one
artifact path and answers green or red. Every case below constructs its own
artifact (or uses the skill's shipped completed-example artifact) and reads
only the checker's printed answer and exit code.

## TC-001 — A complete artifact passes with every criterion green
- **Story**: US1 · **Traces to**: FR-001, FR-006, AC1
- **Given** the skill's shipped completed-example artifact, known to satisfy every observable handoff criterion
- **When** the checker runs on it
- **Then** it exits 0 and its answer reports every one of the five criteria green
- **Pass condition**: `chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && out="$(python3 "$chk" skills/spec-brainstorming/examples/decision-tracker/decision-tracker.md 2>&1)"; rc=$?; test "$rc" -eq 0 && printf '%s\n' "$out" | grep -q 'Direction' && printf '%s\n' "$out" | grep -q 'Problem Statement' && printf '%s\n' "$out" | grep -q 'User Personas' && printf '%s\n' "$out" | grep -q 'Core MVP Features' && printf '%s\n' "$out" | grep -q 'Potential Risk Mitigations'`

## TC-002 — A missing required section fails by name
- **Story**: US1 · **Traces to**: FR-001, AC2
- **Given** an otherwise complete artifact with the Problem Statement section entirely absent
- **When** the checker runs on it
- **Then** it exits 1 and names the missing section as the failed criterion
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -q 'Problem Statement'`

## TC-003 — A present but unfilled section fails
- **Story**: US1 · **Traces to**: FR-001, AC2
- **Given** an otherwise complete artifact whose User Personas heading is present with nothing under it
- **When** the checker runs on it
- **Then** it exits 1 and names that section as present but empty
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -q 'User Personas'`

## TC-004 — An empty artifact fails cleanly, not catastrophically
- **Story**: US1 · **Traces to**: FR-001, AC2
- **Given** a completely empty artifact file
- **When** the checker runs on it
- **Then** it exits 1 naming the required sections, without crashing
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && : > "$tmp/empty.md" && out="$(python3 "$chk" "$tmp/empty.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -Eq 'Direction|Problem Statement|User Personas|Core MVP Features|Potential Risk Mitigations' && ! printf '%s\n' "$out" | grep -q 'Traceback'`

## TC-005 — A surviving template placeholder fails with its stem and line number
- **Story**: US1 · **Traces to**: FR-002, AC2
- **Given** an otherwise complete artifact whose Direction still carries the unfilled placeholder for the selected angle
- **When** the checker runs on it
- **Then** it exits 1 and the failure names both the placeholder stem and the line it sits on
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: <angle or blend>' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && ln="$(grep -nF '<angle or blend>' "$tmp/artifact.md" | cut -d: -f1)" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -qF '<angle or blend>' && printf '%s\n' "$out" | grep -qF "$ln"`

## TC-006 — Legitimate angle-bracket text still passes (standing over-match guard)
- **Story**: US1 · **Traces to**: FR-002, AC1
- **Given** the shipped completed-example artifact with one added sentence that legitimately uses angle brackets for a command argument, none of them a template placeholder
- **When** the checker runs on it
- **Then** it still exits 0 — placeholder detection never over-matches real content
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && cp skills/spec-brainstorming/examples/decision-tracker/decision-tracker.md "$tmp/artifact.md" && printf '%s\n' '' 'The record command takes <name> as its identifier argument.' >> "$tmp/artifact.md" && python3 "$chk" "$tmp/artifact.md"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 0`

## TC-007 — Direction without a rejected angle and reason fails
- **Story**: US1 · **Traces to**: FR-003, AC2
- **Given** an otherwise complete artifact whose Direction records a selection and rationale but no rejected angle with its reason
- **When** the checker runs on it
- **Then** it exits 1 and names the Direction criterion as failed
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -qi 'direction'`

## TC-008 — Core features without a numbered list fails
- **Story**: US1 · **Traces to**: FR-004, AC2
- **Given** an otherwise complete artifact whose Core MVP Features section holds prose but no numbered feature
- **When** the checker runs on it
- **Then** it exits 1 and names the feature-list criterion as failed
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' 'The feature set is chosen with the user in conversation.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -qi 'feature'`

## TC-009 — An empty out-of-scope list fails
- **Story**: US1 · **Traces to**: FR-004, AC2
- **Given** an otherwise complete artifact with a numbered feature list but an out-of-scope heading whose list is empty
- **When** the checker runs on it
- **Then** it exits 1 and names the out-of-scope criterion as failed
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**:' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -qi 'scope'`

## TC-010 — A risk row missing its early warning or mitigation fails
- **Story**: US1 · **Traces to**: FR-005, AC2
- **Given** an otherwise complete artifact whose risk table carries two rows — one missing its early-warning signal, one missing its mitigation or acceptance
- **When** the checker runs on it
- **Then** it exits 1 and reports each defective row as its own failed criterion
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data |  | refresh prompt on open |' '| Adoption stalls | no team sign-up in week one |  |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && test "$(printf '%s\n' "$out" | grep -cE 'Stale data|Adoption stalls')" -ge 2`

## TC-011 — Missing kill criteria fails
- **Story**: US1 · **Traces to**: FR-005, AC2
- **Given** an otherwise complete artifact whose risk section states no kill criteria
- **When** the checker runs on it
- **Then** it exits 1 and names the kill-criteria criterion as failed
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## Problem Statement' '' 'Teams lose decisions made in conversation and re-litigate them later.' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -qi 'kill'`

## TC-012 — Multiple failures are reported one per line with locations
- **Story**: US1 · **Traces to**: FR-006, AC2
- **Given** an artifact failing two independent criteria — a missing section and a surviving placeholder
- **When** the checker runs on it
- **Then** it exits 1 and prints one line per failed criterion, each naming what and where
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: <why this wins>' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && out="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && test "$(printf '%s\n' "$out" | grep -cE 'Problem Statement|<why this wins>')" -ge 2`

## TC-013 — An operator-named artifact path outside the default folder is validated
- **Story**: US1 · **Traces to**: FR-007
- **Given** the shipped completed-example artifact saved under an operator-chosen name in a folder outside the default brainstorms location
- **When** the checker is pointed at that explicit path
- **Then** it validates that exact artifact and exits 0 — no default location is assumed
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && cp skills/spec-brainstorming/examples/decision-tracker/decision-tracker.md "$tmp/handoff-artifact.md" && python3 "$chk" "$tmp/handoff-artifact.md"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 0`

## TC-014 — A named path that does not exist fails by name
- **Story**: US1 · **Traces to**: FR-007
- **Given** an operator-named artifact path pointing at no file
- **When** the checker is pointed at it
- **Then** it exits 1 and names the missing path, never silently substituting a default location
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && out="$(python3 "$chk" "$tmp/does-not-exist.md" 2>&1)"; rc=$?; rm -rf "$tmp"; test "$rc" -eq 1 && printf '%s\n' "$out" | grep -qF 'does-not-exist.md'`

## TC-015 — Repeated checks give byte-identical answers
- **Story**: US1 · **Traces to**: NFR-004
- **Given** the same failing artifact checked twice in a row on the same machine
- **When** both runs finish
- **Then** both print the identical failure report and exit with the identical nonzero code — the answer depends on the artifact alone
- **Pass condition**: `tmp="$(mktemp -d)" && chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && printf '%s\n' '# Demo — design specification' '' '## Direction' '' '- Selected: Minimalist core' '- Rationale: fastest path to observable value' '- Rejected: Visionary platform — displaces tools the team already trusts' '' '## User Personas' '' '### Persona 1 — the on-call triager' '' '- Who: engineer mid-incident.' '- Needs: one-glance status.' '- Failed by: scattered dashboards.' '' '## Core MVP Features' '' '1. Status snapshot — serves the on-call triager. One command prints current state.' '' '**Out of scope (day-one cut list)**: web dashboards, refused to keep day one shippable.' '' '## Potential Risk Mitigations' '' '| Risk (from the panel) | Early warning | Mitigation or acceptance |' '|---|---|---|' '| Stale data | usage drops below five reads a week | refresh prompt on open |' '' '**Kill criteria**: fewer than five uses per week after week three.' > "$tmp/artifact.md" && o1="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; r1=$?; o2="$(python3 "$chk" "$tmp/artifact.md" 2>&1)"; r2=$?; rm -rf "$tmp"; test "$r1" -eq 1 && test "$r1" -eq "$r2" && test "$o1" = "$o2"`

## TC-016 — The checker stays standard-library-only Python
- **Story**: US1 · **Traces to**: NFR-007
- **Given** the checker script
- **When** its imports are inspected
- **Then** every imported module is Python standard library — no third-party or harness dependency enters
- **Pass condition**: `f="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && python3 -c 'import ast,sys; t=ast.parse(open(sys.argv[1]).read()); m={a.name.split(".")[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names}; m|={n.module.split(".")[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and n.module and not n.level}; assert m<=set(sys.stdlib_module_names), sorted(m-set(sys.stdlib_module_names))' "$f"`

## TC-017 — A green check discloses the dealbreaker judgment it cannot make
- **Story**: US2 · **Traces to**: FR-008, AC3
- **Given** a structurally perfect artifact whose Cynic-dealbreaker coverage lives only in the panel digest, not in the artifact
- **When** the checker runs on it
- **Then** it passes every structural criterion and its answer names the digest-to-artifact dealbreaker mapping as a judgment criterion the checker does not decide
- **Pass condition**: `chk="$(ls skills/spec-brainstorming/scripts/*.py | head -1)" && out="$(python3 "$chk" skills/spec-brainstorming/examples/decision-tracker/decision-tracker.md 2>&1)"; rc=$?; test "$rc" -eq 0 && printf '%s\n' "$out" | grep -iq 'dealbreaker' && printf '%s\n' "$out" | grep -iq 'judg'`

## Coverage matrix
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001, TC-002, TC-003, TC-004 | auto |
| FR-002      | TC-005, TC-006 | auto |
| FR-003      | TC-007 | auto |
| FR-004      | TC-008, TC-009 | auto |
| FR-005      | TC-010, TC-011 | auto |
| FR-006      | TC-001, TC-012 | auto |
| FR-007      | TC-013, TC-014 | auto |
| FR-008      | TC-017 | auto |
| NFR-001     | — | n/a — spec declares not applicable |
| NFR-002     | — | n/a — spec declares not applicable |
| NFR-003     | — | n/a — spec declares not applicable |
| NFR-004     | TC-015 | auto |
| NFR-005     | — | n/a — spec declares not applicable |
| NFR-006     | — | n/a — spec declares not applicable |
| NFR-007     | TC-016 | auto |
