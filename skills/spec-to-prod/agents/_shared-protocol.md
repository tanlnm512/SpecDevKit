# Shared agent rules (prepended to every spawn)

Files on disk are the source of truth. You run independently — there is
no shared manifest, no sync log, and no peer-to-peer messaging with
whoever else is in this wave. Everything you need is in your own spawn
payload and the files it points you to; everything the orchestrator needs
back from you is your digest.

## Ownership is exclusive
Touch only the files you own: your one artifact (docs), or your task's
code/test files (implementers). If your work requires changing a file
someone else owns, do NOT edit it — report the gap in your digest instead;
the orchestrator re-briefs the owner.

## Your artifact is the deliverable
Your artifact on disk is the deliverable — not your reply. Ensure it is
complete before you stop; nothing you say back is read as the record.
Return your digest per your brief's contract.

## Universal rules (canonical — your brief does not repeat these)
1. **Citations verbatim** from survey.md, or from your own session's grep
   output — never from memory. A number in an existing doc is a claim;
   re-count it.
2. **Symbols over line numbers**; unknown → `unknown — verify`.
3. **Status lives only in task.md**, derived only from survey evidence — no
   checkboxes or status words in any other file.
4. **IDs (US/FR/AC/T/TC/D) are assigned once and never renumbered.** Dropped
   items are struck through with the `D-###` that killed them, never deleted.
5. **One file per agent.** You write exactly the artifact your brief names
   — nothing else.
6. **You never spawn agents, and you never commit or push.**
