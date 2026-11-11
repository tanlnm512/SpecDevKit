# Intent: <name>

**Type**: feature          <!-- feature | bugfix | hotfix | refactor | upgrade —
                                the work type spec.md inherits; a hotfix is a
                                bugfix small enough for `Tier: tiny` -->
**Effort**: standard       <!-- agent-count effort guess spec.md inherits:
                                standard | large (tiny is a Tier, chosen when
                                spec-design scaffolds spec.md) -->
**Created**: YYYY-MM-DD
**Baseline**: <version @ commit>
<!-- survey.md's baseline shape — version @ HEAD sha of the repo this
     intent was scouted against; the staleness diagnosis reads it
     unchanged, so it stays at the scouted HEAD -->

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-design authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

## Problem
<the problem as the user stated it>
<!-- verbatim beats paraphrase — what hurts, for whom, the cost of
     the status quo; quote the ask first, sharpen it with the user -->

## Audience
<who this serves and what each of them needs>
<!-- one to three named situations, not job titles — like
     spec-discover's personas; say why today fails them -->

## Constraints
<hard bounds the solution must respect>
<!-- stack, scale, deadline, policy — scout-verified facts first;
     every unverified bound is a named assumption, never silent -->

## Questions
<!-- The grilling frontier (references/grilling.md): every open
     question opens as a NEEDS CLARIFICATION marker (the grilling
     vocabulary — the checker's marker scan counts brackets, so write
     markers only on live question lines, never in comments) and
     closes exactly one way — answered (folded into the sections
     above), deferred (Scope out), or a named assumption
     (Assumptions) — the last two only on the user's assent. The pass
     ends when the frontier is empty: no marker survives. Closures
     stay listed here so spec-design inherits the reasoning. -->
- [NEEDS CLARIFICATION: <the open question>]
<!-- replace the seed line above; each closed question becomes a
     bullet of its own: Qn, the question, then — answered: … |
     deferred (Scope out) | assumed: the named assumption -->

## Scope out
<!-- what this intent deliberately leaves out: questions deferred with
     the user's assent, each named with a one-line reason -->

## Assumptions
<!-- named assumptions that closed a question with the user's assent;
     each says what would invalidate it -->

## FR seeds
<!-- EARS-shaped seed requirements — one verb, one system, testable;
     spec.md grows these into the full FR/NFR set -->
- **FR-001**: The system shall <standing capability>.
- **FR-002**: WHEN <trigger>, the system shall <response>.
- **NFR seeds**: <quality bounds the grill surfaced>
<!-- one line: of security, privacy, performance, reliability,
     observability, accessibility, name each family that binds this idea
     with its bound; `none — <reason>` is an answer. spec.md triages all
     six from here. -->

## Handoff
Next: `/spec-design <name>` — the docset (spec.md onward) is authored
there, never here. The Baseline above is what spec-design's survey
re-baselines against.
