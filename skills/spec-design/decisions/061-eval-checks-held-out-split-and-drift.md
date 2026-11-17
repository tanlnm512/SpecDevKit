# D-061: the eval corpus gains checks, a held-out split, and drift pinning

The standing evals stayed conversational while the wider skill
ecosystem moved toward runnable evals. Three contract changes close
the gap without breaking "the runner records; the observer judges":

- **Checks.** A case may pin criteria to `- **Check C<n>**:` shell
  bullets. A conversational case with checks runs them as a dry-run
  sheet under `evals.py run` (nothing recorded, exit reflects the
  sheet) and `validate --repo <scratch>` executes them and merges with
  the transcript verdicts: the check's verdict wins over an observer
  verdict, and a disagreement lands in Findings either way. Criteria
  name no criterion (`Check C9` past the last) or name one twice are a
  malformed case, never a pass. Pilot: spec-build E8 (C2, C3, C5) and
  E9 (C1) — widening happens case-by-case at recording runs, never as
  blanket conversion.
- **Held-out split.** `- **Held-out**: yes` marks the adversarial and
  negative-path cases (15 of 34: spec-build E5/E6/E9, spec-define
  I2/I3, spec-design E3/E8, spec-discover B5, spec-release R2/R4,
  spec-review E1/E6, spec-ship S2/S4/S5). Their Pass criteria are read
  only at judging time — never while authoring or editing the skill —
  so the corpus keeps measuring the skill instead of echoing it.
- **Drift pinning.** drift-check gains the `evals` category: case
  grammar and referential integrity (every result's selector matches
  its filename and a real case; verdicts in range). Coverage and
  freshness stay OUT of the gate — they are `evals.py report`'s view,
  and RELEASE.md § 6's live-eval gate already binds changed behavior
  at release time. Legacy results without a `surface:` stamp are
  reported as unstamped, never restamped.

No LLM-as-judge: the kit is stdlib-only (C-06) and an in-process judge
could not be shared across harnesses (C-03). The mechanical layer
proves end-state artifacts; behavior in transcripts stays judged by an
observer. grade.py's S4 keeps counting recorded results by existence —
the rubric's meaning is unchanged; `report` is the freshness-aware
view beside it.

spec-review E6 and spec-ship S1–S5 need a scratch GitHub remote; they
are recorded when one is provided. Until then they read as `none` in
`report` — a coverage signal, not a CI failure.
