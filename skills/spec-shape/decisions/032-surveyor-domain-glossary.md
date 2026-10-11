# D-032 — Surveyor speaks the repo's domain language

- **Context**: the surveyor words items and the specs/context/
  baseline in whatever vocabulary the grep surface exposes, so a repo
  that keeps a domain glossary gets surveyed in generic terms anyway —
  downstream docs then rename the project's own concepts, and every
  later agent re-derives the mapping. Matt Pocock's `skills` repo
  (`domain-modeling`, and the glossary-reading rule in its `tdd` /
  `diagnosing-bugs` skills) makes the move: read the project's
  GLOSSARY.md/CONTEXT.md first and use its terms, so names, tests,
  and conversation derive from the same domain model.
- **Decision**: the surveyor's method step 1 reads the repo's domain
  glossary when one exists (GLOSSARY.md, CONTEXT.md, docs/glossary*)
  and words items, statuses, and the context files in the project's
  own terms; when none exists, domain terms met while surveying land
  as a line in specs/context/tech.md's conventions for later docs to
  reuse. The kit already models this itself: its own GLOSSARY.md is
  the shared language its briefs are written in.
- **Consequences**: surveys and downstream docs stop inventing
  parallel names for concepts the repo already named — cheaper
  reading, consistent citations, fewer "which thing is this" rounds
  in clarify. No new artifact, no contract change (C-04: reuse of the
  repo's own glossary, not a new mechanism). Serves eval cases E1
  (happy-path pipeline over a repo that keeps a glossary) and E4
  (resume: consistent vocabulary across sessions).
