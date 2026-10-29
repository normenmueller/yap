# Return point — #18 implementation review

The owner approved the implementation scope for
[#18](https://github.com/normenmueller/yap/issues/18) on October 29, 2026.
[PR #22](https://github.com/normenmueller/yap/pull/22) delivers the candidate
implementation at `5dec43a`; owner acceptance and merge remain pending.
`normenmueller` is the requested reviewer. The Issue owns the detailed scope and
next action; the yap Project owns live status and order.

Continue in `feat/18-named-workspace-links`, whose matching worktree and branch
were verified on base `7e9c744`. Both ordinary greetings recover here: report the
observed state, support the owner's implementation review and await feedback.
Do not prepare another Issue or infer acceptance from the approved design,
passing tests, expert review or this handoff. BEHAVIOR owns session boundaries.

Activity/area sources now own named YAML `wsp` maps and navigation consistently
uses `wsp/NAME`. The [authoring guide](../doc/authoring.md#local-workspaces) owns
path, preservation and migration rules; the [user guide](../doc/README.md) owns
setup and commands. PyYAML is declared in `requirements.txt`. Consumer integration
must separately install dependencies and explicitly migrate any legacy bindings.
No consumer revision, real user data or external workspace has been migrated.
Instance owners control source-path inclusion in their own Git history;
workspace metadata and target contents remain excluded from generated output.

`trunk` retains accepted #20 / merged PR #21 (`cf461b0`), #17 / PR #19,
#15 / PR #16 and #1 / PR #2. #20 is closed and Done. Its preserved local synthetic
review navigation remains in optional ignored `.yap/cfg/session.md`.
[#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14) remains separate
on `docs/3-architecture`; preserve that work and its return point. TypeScript and
broader architecture remain proposals. #4 and #13 are not selected here.

<details>
<summary>Implementation review and verification evidence</summary>

Independent architecture and filesystem reviewers resolved anchored-YAML edit
side effects, case-spelling collisions, navigation cycles and misplaced metadata.
Their final scoped reviews had no remaining findings. A separate author supplied
migration and navigation regression tests. These reviews do not replace owner
acceptance.

The full suite passed 281 tests with browser access. After two additional CLI
migration/argument tests, all six CLI tests passed; the architecture reviewer
independently passed 60 focused tests. The earlier sandbox-only full run failed
only to start the isolated browser. Runtime changes are in `5dec43a`.

A synthetic full report/export built successfully. Checks covered 68 site/export
files, including seven PDFs per copy via text extraction, plus the model cache:
no workspace-path or target-content markers. Site/export SHA-256 inventories
matched; aliases shared a target and an unavailable target warned without
preventing output. Ignored review evidence stays in this Issue's worktree.

</details>
