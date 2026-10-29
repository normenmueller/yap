# Application development behavior

Explicit user instructions and host constraints take precedence. Read BEHAVIOR,
CONTEXT and STATE, then verify the actual checkout, branch, worktrees, remote and
relevant changes. Preserve unrelated, ignored and private material. A worktree,
local note or old approval does not grant execution or cross-repository authority.

Keep this application reusable. Public source, history, documentation and agent
context must contain no private portfolio data, names, paths or workflow links.
Select instances explicitly; no sibling lookup or copied implementation. Instance
teams and application development own separate context, configuration and runtime.
AI assistance does not establish accepted ai4X curation or activate agents.

Write code, engineering records and agent context in US English; preserve authored
content in its original language. Target English/German interfaces; distinguish
the retained German baseline from undelivered localization. Collaborate in the
user's language. Explain consequences plainly and always say what the user needs
to do next, or that no action is needed.

Apply the PO reading rule to documents, Issues and PRs: short, accessible opening;
technical evidence and architecture at the end in collapsed details; team notes
further collapsed or in their authoritative records. Keep product copy free of
internal implementation notes. Prefer lean semantic structure and small cohesive
changes; avoid speculative machinery, duplicate rules and parallel implementations.

## Work and acceptance

The application's Project owns live status/order; Issues own scope and next
action, source files own facts. Keep them current after meaningful changes.
Ready is the owner's approval of the refined implementation scope, not permission
to self-accept a result. GitHub Approve on a delivered implementation authorizes
merge after required checks; design approval accepts the design only. Changes
after approval need the affected review. Do not infer acceptance from a build,
chosen copy, publication or this handoff. Never force-push or discard unknown work.

Use an issue-linked branch for engineering work. Keep local/remote branch names
identical and match new worktree paths to the branch, preserving existing PR and
review history. Use Git for history, not backup folders. Preserve assignees and
owner order; relocated issues are not evidence of delivered functionality.

Work on one selected Issue at a time. After completion, finish merge, cleanup
and handoff, then end/delete that session before preparing the next Issue.
An explicitly agreed interruption also requires a recorded return point and
this session boundary. Start a fresh Codex CLI session in `trunk`, without resume,
only to verify the selected Issue and base revision, create or verify its
issue-linked branch and matching worktree, and record the verified handoff.
Reuse existing preparation; do not recreate branches or worktrees blindly.

Then end/delete the `trunk` preparation session and start another fresh session,
without resume, in the selected `feat/...` or `fix/...` worktree. All Issue-specific
analysis, refinement, decisions, implementation, tests and review belong in that
Issue's worktree/session. Preparation does not approve implementation scope.
Verify the session's actual working directory, branch, instructions and write
scope before continuing; an individual command's working directory does not
relocate the session. Keep implementation, tests and ignored development evidence
in that worktree. Ordinary greetings follow these same boundaries.

After a verified successful merge, delete the completed feature branch locally
and remotely. Remove its worktree after preserving ignored/private material and
verifying that no unmerged work remains. During preparation and cleanup, remove
empty parent directories, including `fix/` and `feat/`. Preserve active branches
and PR history.
Use only the explicitly selected provider profile; never switch shared login.
When creating a managed PR, request `normenmueller` as reviewer immediately,
including documentation drafts. Preserve other reviewers; assignment is not a
review request, and a request is not approval.

Use proportionate verification and report its revision/scope accurately. Reuse
valid evidence for metadata-only changes. Keep one owner for every domain fact;
views, Git and prose do not establish source relationships or measured impact.
Consult [TEAM.md](TEAM.md) for required expertise and independent review. For
material memory changes, independently assess five criteria at 0–2 each: recovery,
factual/source consistency, authority/preservation, concision and references.
Resolve findings and recheck before substantive work continues. A scoped 10/10
is required by the owner; do not coach scores or create a review registry.

## Cold Start and fresh-session recovery

Cold Start prepares the handoff now so the owner can end the session. It is not a
startup command. Reconcile active contexts and relevant configuration, verify
references and necessary checks, update owning Issues/Project, independently
review the handoff, commit/push authorized changes and verify remote/clean state.
Keep unfinished work and user decisions explicit; do not merge for tidiness.
The request authorizes this closeout, not new feature work or private publication.
Stop after reporting the verified handoff; the owner ends/deletes the session.

A new session reads AGENTS and these records automatically, without resume or
old chat. If `.yap/cfg/session.md` exists, read it after STATE for private local
review navigation. It is optional, ignored, and grants no authority; never copy
its contents into public artifacts. Without it, generic application recovery
still works; ask for an external location only if the current task needs it.

- “Hi Gertrud, wo stehen wir?”: give a concise observed status, pending decision
  and proposed next action, then wait. Read-only recovery is allowed.
- “Hi Gertrud, weiter geht's!”: give the same brief status, then follow the actual
  authorized return point. If it is human review, support that review and wait
  for feedback; do not start another queue item or manufacture a decision.
- Equivalent ordinary greetings work too. No special phrase is required. A new
  session does not repeat closeout or grant new acceptance. Explicit user holds
  and session-specific choices take precedence over Board order or old memory.
