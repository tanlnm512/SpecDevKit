# Domain language — the vocabulary primitive

The kit's shared-language discipline for agents writing about a
repo (extracted from the scout's survey lens, D-032/D-039).

- **Read the project's glossary first.** If the repo keeps a domain
  glossary — GLOSSARY.md, CONTEXT.md, docs/glossary* — read it
  before writing a word, and word items, statuses, digests, and
  docs in the project's own terms. The survey speaks the codebase's
  language, not a generic one; test names and interface vocabulary
  derive from the same domain model.
- **No glossary exists? Capture one line.** The domain terms you
  meet while working land as a line in specs/context/tech.md's
  conventions for the later docs to reuse — the cheapest possible
  seed of a shared language, grown where the next agent will look.
- **Never coin a parallel name** for a concept the repo already
  named. A "session" the code calls a "lease" costs every later
  reader a mapping, and drifts on the first refactor.
