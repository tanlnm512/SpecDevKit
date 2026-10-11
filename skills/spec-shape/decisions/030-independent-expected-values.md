# D-030 — Expected values from an independent source of truth

- **Context**: the kit-wide engineering rules (`rules/
  engineering-rules.md`, injected into every spawn payload via
  `_shared-protocol.md` and the code-review fixer brief — D-028)
  bound what deserves a test and where the owner test lives, but not
  where a test's expected values come from. The common LLM-authored
  failure mode (named in Matt Pocock's `skills` repo, `tdd` skill's
  anti-patterns) is the tautological test: the assertion recomputes
  the expected value the way the code does — `expect(add(a, b)).
  toBe(a + b)`, a snapshot derived by the same procedure — so it
  passes by construction and can never disagree with the code.
- **Decision**: one bullet added to § Before adding a test: expected
  values come from an independent source of truth — a known-good
  literal, a worked example, or the spec — never from recomputing
  them with the same logic the code under test uses; a test whose
  assertion cannot disagree with the code proves nothing. Carriers
  regenerated with `tools/kit-rules.py`. The spec-code-review quality
  lens names the same shape explicitly in its "tests that cannot
  fail" rubric (D-015's CHANGELOG entry records it), so authoring
  (implementers, qa) and reviewing (quality lens) enforce the same
  rule from both ends.
- **Consequences**: implementers and the fix loop stop landing tests
  that verify nothing while looking green; audit.py's mutation pass
  (D-027) catches fewer tautologies because fewer get written.
  Serves eval cases spec-to-prod/E2 (the regression test must fail
  on the pre-fix code for the intended reason — a recomputed
  expectation usually survives the bug) and spec-code-review/E2
  (seeded test-facing defect 4's family).
