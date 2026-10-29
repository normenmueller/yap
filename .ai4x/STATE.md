# Return point — #17 merged; board reconciliation pending

[#17](https://github.com/normenmueller/yap/issues/17) is complete. The owner
approved [PR #19](https://github.com/normenmueller/yap/pull/19), which was merged
into `trunk` on October 29, 2026. The Issue is closed. The accepted application
baseline includes #17, #15 and #1 / merged PR #2.

Next: reconcile the missing entries in the
[yap Project](https://github.com/users/normenmueller/projects/5): accepted #15
and #17 belong in Done; open proposal #18 belongs in Backlog. The current
`gertrud-ai4x` GitHub profile can read Projects but cannot write them. An owner
must update these entries or grant the profile the required permission. Preserve
existing item order, assignees and statuses; do not switch the shared login.

The owner chose to end this session and start a fresh session from `trunk`.
No next implementation item or consumer revision has been selected. After the
board reconciliation, wait for the owner's choice; create an issue-linked branch
and matching worktree for selected engineering work. Preserve the separate
`docs/3-architecture` discussion and local development evidence. BEHAVIOR owns
fresh-session recovery; no old chat or resume is needed.

The homepage now has a linked portfolio heading, product introduction and the
assistant request-panel design. The heading opens the existing Activity/Performance
collection. Optional `branding.assistant` and `branding.assistant_credit` supply
explicit display metadata only. The input does not submit or save text, and
creation remains disabled; no assistant/provider is activated. German remains
the delivered interface baseline; #6 owns localization.

Consumer revision selection and integration remain separate and require
instance-owned verification.

The Python application still defaults to `pfo/asp`, with an optional
instance-relative `sources.aspirations` setting in `yap.json`. Selected sources
share reading, validation, change detection and publication-reference handling.
There is no implicit `pfo/okr` lookup or source creation. Instances still using
that path need their own explicit selection or manual move/reference repair.
The [authoring guide](../doc/authoring.md#objectives-and-key-results) owns usage.
#15 / [PR #16](https://github.com/normenmueller/yap/pull/16) owns the accepted
aspiration-source delivery and its verification evidence.

[#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14) remains separate
on `docs/3-architecture`. Its TypeScript and broader directory contracts remain
proposals. #4 still needs its own approved foundation scope; README work remains
#13. [#18](https://github.com/normenmueller/yap/issues/18) separately records the
proposed workspace map. None is selected by this acceptance.

<details>
<summary>Delivery and verification evidence</summary>

The owner `normenmueller` approved PR #19 at
`d9c721edd473fe73662477a91c2c0d8f988d001f`. The verified merge is
`ce721ff86ec1f9a55fb88425a6b9e2d9377a6d36`. Issue #17 has no Project item.
Verify actual Git/remote state before continuing; completion-note changes are
memory only.

A full Project/Issue audit found #15, #17 and #18 absent from all yap Project
items. Board, Backlog, Focus and Overview share that Project. Existing item
statuses match the observed Issue states; #3 remains In progress, #5 Paused and
#1 Done. Adding #15 was rejected by GitHub with `INSUFFICIENT_SCOPES`: the active
profile has `read:project` but requires `project` for this mutation. No Project
mutation succeeded. Other users' or repositories' boards were not audited.

The completed feature branch was deleted locally and remotely, its clean worktree
removed and its empty parent directory removed. All 118 ignored review files were
moved unchanged to the application's ignored
`.yap/local/build/homepage-review-pr19/` under `trunk`, with SHA-256 comparison.
The relocated `nap.html` and its local links/assets were checked.

PR #19 records 255 passing regression tests, synthetic full-report/incremental
checks and offline desktop/narrow checks at 1440px and 390px at the implementation
head. In this acceptance session, a synthetic report was freshly generated from
that head and homepage/collection link and asset targets were checked. The owner
reviewed the local preview and approved the unchanged implementation on GitHub.
No separate independent implementation review is claimed. Consumer revision
selection and integration remain separate and require instance-owned verification.


#15 / [PR #16](https://github.com/normenmueller/yap/pull/16) was accepted at
`a3c7f09` and merged as `f8d2d3bc16d675786e7d6bd75ea439526631f25d`; its
254-test implementation evidence remains in that delivery record.

</details>
