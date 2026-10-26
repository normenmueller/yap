# Return point — owner review of #15 / PR #16

Next: support the owner's review of [PR #16](https://github.com/normenmueller/yap/pull/16)
for [#15](https://github.com/normenmueller/yap/issues/15), then wait for feedback.
Implementation revision `cf57907` is published on `feat/15-aspiration-source`;
`normenmueller` was requested as reviewer when the PR was created. Verify actual
Git, remote and review/check state. The Issue owns scope and acceptance; the PR
owns delivery evidence. Owner acceptance and merge remain pending. Do not start
another queue item or change a consumer revision during this review return point.

The implementation uses `pfo/asp` by default, with an optional instance-relative
`sources.aspirations` setting in `yap.json`. Reading, validation, change detection
and publication references share the selected path. General manifest loading adds
only structural checks for this setting; content/build validate the filesystem
before discovery, hashing or cache reuse. There is no implicit `pfo/okr` lookup
or creation. Existing sources need a consumer-owned manual move/reference repair
or explicit selection of their existing location. Source structure, Objective/KR
semantics, internal styling and publication destinations retain their contracts.
The [authoring guide](../doc/authoring.md#objectives-and-key-results) owns usage.

Verification at `cf57907`: all 254 regression tests passed. Four disposable
synthetic instances covered the default, a deeper path with spaces, explicitly
selected `pfo/okr` and `plans/work/aspirations`. Real report/open, HTML/browser,
PDF destination and cross-link checks passed. Incremental Objective prose,
KR measurement and contribution edits refreshed the appropriate outputs;
measurement-only changes retained existing PDF contents. Normal operations
preserved source/configuration bytes and saved/unsaved perspectives. Independent
AI implementation review found no unresolved findings after corrections and
rechecks. These are implementation evidence, not owner acceptance or consumer
integration. Memory-only changes after this revision do not alter runtime bytes.

The accepted baseline remains #1 / merged PR #2. [#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14)
stays separate on `docs/3-architecture`; its TypeScript and broader directory
contracts remain proposals. #4 still needs its own approved foundation scope;
README work remains #13. Existing Project order is unchanged; the owner's
explicit selection of #15 governs this review. BEHAVIOR owns recovery, reviewer
requests and acceptance boundaries.
