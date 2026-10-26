# Return point — implement #15 on its prepared feature branch

Next: implement [#15](https://github.com/normenmueller/yap/issues/15) on
`feat/15-aspiration-source`. The owner approved its bounded scope and chose this
work for the next fresh session. The native Issue-linked remote branch and
matching local worktree were prepared from `trunk` at `98b1318`; verify actual
Git/remote state and worktree location. A session starting on `trunk` routes this
work to the prepared feature worktree; preserve the separate architecture branch.
The Issue owns the full scope, design, acceptance checks and next action.

The approved change makes `pfo/asp` the default aspiration-source root, with an
optional instance-relative `sources.aspirations` override in `yap.json`. Remove
implicit `pfo/okr` lookup or creation; an old-named path remains usable when
explicitly selected. Removing `okr` concerns the source directory only. Keep the
existing source structure, semantics, internal styling and publication targets.
Manual source moves and reference repairs remain consumer-owned.

Independent AI architecture/filesystem and Python assessments, followed by a
separate AI design review, found no unresolved design blockers. The review's
configuration-boundary finding is resolved in the Issue's design: general
manifest parsing stays structural; content/build validate selected source paths
before discovery, hashing or cache reuse. These are design assessments only.

No #15 implementation or runtime verification has started. The current Python
code still uses `pfo/okr`; the new default and override are not delivered. The
accepted baseline remains #1 / merged PR #2. Prior Python regression, report and
browser evidence applies only to unchanged implementation bytes. Implement,
verify the Issue's synthetic and regression cases, inspect generated output and
obtain independent implementation review before requesting owner acceptance.
Do not select a consumer revision or migrate an instance as part of this work.

[#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14) remains a separate
future architecture discussion on `docs/3-architecture`, not the current return
point. Its TypeScript and broader directory contracts remain proposals;
[#4](https://github.com/normenmueller/yap/issues/4) still needs its own approved
foundation scope. README work remains #13. Project order is unchanged; this
explicit owner choice governs the continuation. BEHAVIOR owns recovery, reviewer
requests and acceptance boundaries.
