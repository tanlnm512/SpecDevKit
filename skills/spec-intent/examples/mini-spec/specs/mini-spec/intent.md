# Intent: mini-calc-multiply

**Status**: validated
**Tier**: standard
**Created**: 2026-09-08
**Baseline**: mini-calc v1 @ 3fa9c21

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-shape authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

## Problem
"I have a calculator CLI but it only adds — I need multiplication for
the inventory scripts." The repo confirms it: `repo/calc.py` ships
`add` with no `multiply`, and the inventory workaround (repeated
addition in a shell loop) is slow and wrong for negative stock
adjustments.

## Audience
- The inventory script author — needs a single-call multiply so the
  loop disappears; today's workaround fails them on negatives.
- A future contributor adding percent math — needs multiply as a
  primitive they can compose, not a reimplementation.

## Constraints
- The CLI surface stays `python3 calc.py <verb> <args>` — scout fact:
  every existing verb follows it (`repo/calc.py:main`).
- Stdlib only, no new dependencies (the repo has none and CI runs
  bare `python3 -m unittest`).

## Questions
- Q1: integer-only, or decimals too? — answered: integer-only; the
  inventory scripts pass ints, and the example spec's ACs say
  integers.
- Q2: what happens on non-integer input? — assumed: a nonzero exit
  with a one-line error, matching `add`'s existing behavior.

## FR seeds
- **FR-001**: The system shall multiply two integers and print the
  product.
- **FR-002**: WHEN input is not an integer, the system shall exit
  nonzero with a one-line error.

## Handoff
Next: `/spec-gen mini-calc-multiply` — the docset (spec.md onward) is
authored there, never here. The Baseline above is what shape's survey
re-baselines against.
