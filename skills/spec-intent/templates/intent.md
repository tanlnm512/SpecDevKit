# Intent: <name>

**Status**: draft          <!-- draft while grilling → validated once
                                `check.py --intent-only` exits 0 (the
                                handoff gate below) -->
**Tier**: standard         <!-- the effort guess spec.md inherits:
                                tiny | standard | large (SKILL.md §
                                Effort scaling) -->
**Created**: YYYY-MM-DD
**Baseline**: <version @ commit>
<!-- survey.md's baseline shape — version @ HEAD sha of the repo this
     intent was scouted against; the staleness diagnosis reads it
     unchanged, so it stays at the scouted HEAD -->

The intake artifact — WHAT the user wants and WHY, in their words,
before any docset file exists. spec-shape authors spec.md from here;
nothing in `specs/<name>/` beyond this file is intent's to write.

## Problem
<the problem as the user stated it>
<!-- verbatim beats paraphrase — what hurts, for whom, the cost of
     the status quo; quote the ask first, sharpen it with the user -->

## Audience
<who this serves and what each of them needs>
<!-- one to three named situations, not job titles — like
     spec-brainstorming's personas; say why today fails them -->

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
     above), deferred (Scope out), or a named assumption. The pass
     ends when the frontier is empty: no marker survives. Closures
     stay listed here so spec-shape inherits the reasoning. -->
- [NEEDS CLARIFICATION: <the open question>]
<!-- replace the seed line above; each closed question becomes a
     bullet of its own: Qn, the question, then — answered: … |
     deferred (Scope out) | assumed: the named assumption -->

## FR seeds
<!-- EARS-shaped seed requirements — one verb, one system, testable;
     spec.md grows these into the full FR/NFR set -->
- **FR-001**: The system shall <standing capability>.
- **FR-002**: WHEN <trigger>, the system shall <response>.

## Handoff
Next: `/spec-shape <name>` — the docset (spec.md onward) is authored
there, never here. The Baseline above is what shape's survey
re-baselines against.
