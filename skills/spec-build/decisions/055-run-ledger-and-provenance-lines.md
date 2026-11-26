# D-055: write provenance from the orchestrator — every verb a ledger row, every digest file one orchestrator-appended line

D-040 made the developer's digest file the evidence `mark.py land`
reads and D-054 gave it three states. What produced a digest was still
nowhere: the model and the harness were not recorded at all, the role
was a file name, and the payload the digest answered sat in
`spawns/wave-<N>/` until archive removed it with the digest. Telemetry
counted a landing per machine and named a run id; it held no request.
An agent could also write any line into its own digest file, and a
line claiming a model or a harness read exactly like a record.

**Decision** (the ledger module, the sweep and graph.py are canonical
in spec-design's D-075; adopted here in the same words — this skill's
half is the verbs, the sweep before land and fail, and the retro fold):

1. **`specs/<name>/runs/ledger.jsonl` is the run ledger — append-only,
   orchestrator-written, never status.** One JSON row per orchestrator
   event: `ts`, `skill`, `event`, then the event's own fields among
   run, wave, task, node, role, lens, stem, payload, input, model,
   harness, digest and outcome — a null field is omitted. The events
   are `run_start` and `run_end` (`graph.py --run`, with its stop
   reason as `outcome` and the gate it paused at as `node`), `wave`
   (one row per payload at every `--emit-spawns`), `digest` and
   `digest_malformed` (the sweep), and `claim`, `land`, `fail`,
   `release`, `drop` — every verb of this skill. Only orchestrator
   scripts append to it, each row one line under the spec's
   `.task.lock`; a verb writes its row inside the lock hold that wrote
   its marker, so a landing and the record of what landed are written
   together. Nothing reads it as state. It is repo evidence —
   committable, no `.gitignore` — and `archive.sh` moves it with the
   spec, so it outlives the `digests/` tree it describes.
2. **A row records the request, never an agent's claim.** `claim`
   writes one row per task: the run id, the wave, the payload's sha256-12
   taken again from the file the emit wrote, the developer brief's
   frontmatter `model:` value, and the harness — `mark.py claim
   --harness <name>` is a new optional flag, recorded verbatim and
   `unknown` when ungiven; `graph.py --run` passes its own `--harness`
   on to the claim it makes and to the claim command it prints. `land`
   carries the digest's sha and its status word, `fail` the status word
   of the attested digest, `release` its reason class, and every verb
   the run id of the claim it acted on.
3. **A verb's row is written when the verb acted.** A completed
   transition appends its row; a refused verb is no event; a usage
   error or a busy lock writes nothing. A ledger that cannot be written
   is reported as a warning and never undoes a marker — evidence never
   holds the workflow back.
4. **The provenance sweep runs before `land` and `fail` read a
   digest.** Every `digests/wave-*/<stem>.md` with no provenance line
   yet is validated with its role's schema; a valid file gains ONE
   appended line and a `digest` row whose `digest` is the file's own
   sha, taken before the line was appended:

       provenance: run <id> · role <role> · lens <lens> · model <model> · harness <harness> · payload <sha12> · input <fp12> · recorded <UTC ISO>

   The line is rendered from the ledger's `wave` row for that wave and
   stem — the request that produced the digest — and from nothing
   else; where no such row exists the line says `none` for every
   request fact and the digest is still read on its own merits.
5. **A provenance line is the orchestrator's, and the ledger says
   so.** The line verifies only against a `digest` row of the same
   wave and stem carrying the same digest sha and rendering the same
   line. A file whose line no row vouches for — written by hand,
   edited after the sweep, or copied whole from another file — is
   malformed, like a file that fails its schema: the sweep leaves it
   untouched, records `digest_malformed` (outcome `unverified` or
   `malformed`, once per content), and names it as a fix and run
   again; `land` refuses it with D-054's malformed-digest refusal and
   never talks over it with `--digest`; the resume view reads it as
   malformed. The digest schema ignores the line itself.
6. **Agents are never asked to write or copy provenance.** The
   developer's file is its digest alone — the payload's digest-file
   instruction is unchanged, and the round-4 `Model:` header line is
   untouched; the orchestrator's append is the record of what the
   orchestrator spawned and saw.
7. **`retro.py` folds the ledger beside the digest rows**: one table
   row per recorded digest with its task, wave, run, role, lens, model,
   harness, payload sha, input fingerprint, digest sha and outcome,
   then the malformed count — facts, never prose, and the only
   provenance that survives archive.

**Consequences**: a landing can be traced to the payload, the brief's
model and the harness that were asked for, and a provenance line an
agent writes is refused rather than believed. The costs if this is
wrong: an in-flight spec's digests written before this decision join
no wave row and record `none` for their request; a digest produced by
an earlier emit of the same wave number joins the later `wave` row,
the closest fact the orchestrator holds; `model` and `harness`
describe the request, not the model a harness resolved (an open
assumption in HARNESS-FACTS.md), and a round-4 payload's one model
step up is visible only in the `fail` rows that precede it; and every
`graph.py` report now writes when a digest is waiting for its line.
