# D-075: record every orchestrator event in the run ledger — provenance is written by the orchestrator, never by the agent

D-040 made a digest file the evidence `mark.py land` reads, and
D-054 gave it a schema; nothing recorded what produced it. The role
was implicit in a file name, the model and the harness were nowhere,
and the payload the digest answered sat in `spawns/wave-<N>/` beside
it until archive deleted both. The local telemetry counts events per
machine and names a run id; it holds no request. An agent's file was
also the one place a line about its own provenance could be written,
and no reader could tell such a line from a record.

**Decision** (the ledger module and graph.py are canonical here; the
verbs and the retro fold are adopted in spec-build's D-055):

1. **`specs/<name>/runs/ledger.jsonl` is the run ledger — append-only,
   orchestrator-written, never status.** One JSON row per orchestrator
   event: `ts`, `skill`, `event`, then whichever of run, wave, task,
   node, role, lens, stem, payload, input, model, harness, digest and
   outcome the event carries, in that order — a null field is omitted,
   never written. The events are `run_start` and `run_end` (`graph.py
   --run`, the stop reason as `outcome` and the gate it paused at as
   `node`), `wave` (one row per payload at every `--emit-spawns`),
   `digest` and `digest_malformed` (the sweep), and the five `mark.py`
   verbs. Only orchestrator scripts append to it, each row one line
   under the spec's `.task.lock`; nothing reads it as state. It is
   repo evidence — committable, no `.gitignore` — and moves with the
   spec at archive.
2. **A row records the request, never an agent's claim.** Role, lens,
   node and stem come from the payload item; `payload` is the sha256-12
   of the payload file the emit wrote; `input` is the docset
   fingerprint at the emit; `model` is the brief's frontmatter
   `model:` value, `inherit` when it names none; `harness` is the
   string a new optional flag, `graph.py --run|--emit-spawns
   --harness <name>`, gave — recorded verbatim, `unknown` when
   ungiven. The core records that string and never branches on it
   (C-03).
3. **The provenance sweep runs at the start of every `graph.py`
   invocation that touches a spec** — report, explain, emit, run — and
   never in `--launch-check` or an invocation refused at the gate.
   Every `digests/wave-*/<stem>.md` that carries no provenance line is
   validated with its role's schema, under the lens its wave row names.
   A valid file gains ONE appended line and a `digest` row whose
   `digest` is the file's own sha256-12, taken before the line was
   appended:

       provenance: run <id> · role <role> · lens <lens> · model <model> · harness <harness> · payload <sha12> · input <fp12> · recorded <UTC ISO>

   The line is rendered from the ledger's `wave` row for that wave and
   stem and from nothing else. A file whose wave has no such row is
   recorded as seen with `none` for every request fact — a digest
   nobody's emit asked for is never given a request.
4. **A provenance line is the orchestrator's, and the ledger says
   so.** The line in a file verifies only against a `digest` row of the
   same wave and stem that carries the same digest sha and renders the
   same line. A file whose line no row vouches for — written by hand,
   edited after the sweep, or copied whole from another file — is
   malformed: `specstate.digests_on_file` reports it so, the sweep
   leaves it untouched and records `digest_malformed` with outcome
   `unverified`, and the orchestrator's output names it as a fix and
   run again. A file that fails its schema is left as it is and
   recorded the same way, once per content, with outcome `malformed`.
   The schema validators in `scripts/digests.py` ignore the
   `provenance:` line itself.
5. **Agents are never asked to write or copy provenance.** The agent's
   file is its digest alone; the orchestrator's append is the record of
   what the orchestrator spawned and saw. The payload is untouched by
   the ledger — the round-4 `Model:` line, every header and every
   section are written exactly as before.

**Consequences**: a digest can be traced to the request that produced
it, past archive, and a provenance line an agent writes is refused
rather than believed. The costs if this is wrong: a report is no
longer a pure read when a digest file is waiting for its line — a
digests/ tree with nothing to sweep still writes nothing; a ledger
that lost its wave rows records `none` instead of guessing a request;
a digest produced by an earlier emit of the same wave number joins the
later `wave` row, the closest fact the orchestrator holds; `model` and
`harness` describe the request, not the model a harness resolved — an
open assumption in HARNESS-FACTS.md; a run that dies by exception
leaves a `run_start` with no `run_end`, which is itself the record;
and a ledger row written where the marker write could not be rolled
back is reported as a warning and the marker stands.
