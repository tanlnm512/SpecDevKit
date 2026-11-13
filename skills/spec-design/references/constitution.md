# The constitution (with the user, before approve)

`specs/CONSTITUTION.md` holds the repo's non-negotiable articles.
scaffold.sh creates it from the template on the repo's first spec;
filling it is this step and no agent's. Unfilled (`check.py <spec-dir>
--constitution` exits 1) it binds nothing: payloads do not cite it,
and `check.py` WARNs on the repo's first spec and FAILs from the
second. Once per repo, while the first waves run, draft it with the
user: propose three to five MUST-strength articles from the intent's
Constraints and the repo's conventions, one rationale line each; the
user confirms or rewords each, and their wording wins. In a repo with
existing code, let the analyst find the conventions: `graph.py
<spec-dir> --emit-spawns --repair constitution` emits `constitution.md`
(analyst + constitution lens), which returns proposed articles each
cited to repo evidence and writes nothing — they are proposals until
the user confirms them. It is due
before the approve gate — the contract review reads the docset
against it. Later amendments append; never weaken an article
silently.
