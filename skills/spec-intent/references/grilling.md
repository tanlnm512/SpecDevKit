# Grilling — the clarify-pass primitive

The model-invoked interview discipline the spec-to-prod clarify node
runs (extracted from the playbook, D-039 — one home, invoked by the
orchestrator; the rigid single-question flow of spec-brainstorming's
stages 1/4 is a deliberate dialect of this primitive, not a copy).

## The model

Map the draft's gaps — missing acceptance criteria, undefined edge
cases, vague FRs, open NEEDS CLARIFICATION markers — as a **design
tree**: every open decision branches into the decisions that hang off
it. Work the tree in **rounds**. The **frontier** is every question
whose prerequisites are already settled — askable now without
guessing at an answer you haven't heard yet. A question whose answer
depends on another still-open question belongs to a *later* round,
never this one.

## The round

Ask the *whole* frontier in one batched round. Each question:
numbered, titled, says why it matters, offers 2–3 viable options
where useful, and carries a recommended answer:

```
❓ **Q1** — **<question title>**: <body>
➡️ <recommended answer>
---
❓ **Q2** — **<question title>**: <body>
➡️ <recommended answer>
```

- Word each question so **"yes" accepts the recommended answer** —
  the user can confirm the ➡️ with one word.
- **Finding facts is never the user's job** — "does X already exist /
  is Y already handled" is a fact, not a decision: grep/read the repo
  yourself (or spawn a scoped scout probe for anything substantial)
  and put only genuine judgment calls to the user.
- Don't block the round on a running check — only the questions
  downstream of it wait; ask the rest of the frontier now.

## The non-answer rule (hard stop)

A round put to the user is a HUMAN gate — an unanswered round is not
an answer. Some harness modes resolve the ask without ever waiting,
and an empty or skipped reply is the same thing. On any non-answer:
print the round exactly as formatted and **end the turn there** — do
not adopt the ➡️ recommendations, do not resolve markers yourself, do
not spawn anything. Stopping is safe by construction while open
markers hold the graph at `clarify`; the run resumes from doc state
when the user's answers arrive. The recommendation exists to make
answering one glance cheap, not to make the round optional.

## Closing

Each round's answers reshape the tree and push the frontier outward;
recompute and ask the next round. The pass ends when the frontier is
**empty** — never at a fixed question count; a tree that keeps
sprouting branches instead of closing is a signal to split the
feature, not to push more rounds. Every question closes in exactly
one of three states — answered (resolved into spec.md), explicitly
deferred (Scope out), or a named assumption (Assumptions & risks) —
never left open. One ambiguity caught here is one ambiguity a
downstream agent never sees.
