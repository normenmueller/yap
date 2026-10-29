# Return point — #20 visually accepted; implementation review pending

The owner accepted the visible homepage alignment for
[#20](https://github.com/normenmueller/yap/issues/20) on October 29, 2026.
[PR #21](https://github.com/normenmueller/yap/pull/21) contains the candidate on
`fix/20-homepage-alignment`. GitHub implementation approval and merge remain
pending. The [yap Project](https://github.com/users/normenmueller/projects/5)
keeps #20 In review.

End/delete the current `trunk` session after this verified handoff. Start a fresh
session in the matching `fix/20-homepage-alignment` worktree beside `trunk`.
Read the entry records and verify the actual checkout and write scope there.
The return point is the owner's GitHub implementation review of PR #21; support
that review and wait for feedback. Do not repeat implementation or infer merge
approval from the owner's visual agreement. BEHAVIOR owns the session boundary.

The owner selected one Issue at a time: #20 first, then
[#18](https://github.com/normenmueller/yap/issues/18). #18 remains in Backlog,
with no feature branch or implementation started. Its workspace-map contract
and migration need refinement before implementation. When #18 starts, prepare
its own `feat/18-...` branch, matching worktree and fresh session.

`trunk` retains the accepted Python baseline: #17 / merged PR #19, #15 / merged
PR #16 and #1 / merged PR #2. The #20 runtime change remains on its Fix branch.
Consumer revision selection and integration remain separate and require
instance-owned verification. No consumer revision has been changed here.

[#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14) remains separate
on `docs/3-architecture`; preserve that work and its return point. Its TypeScript
and broader directory contracts remain proposals. #4 still needs an approved
foundation scope; README work remains #13. Neither is selected by this handoff.

<details>
<summary>Implementation and verification evidence</summary>

PR #21's runtime commit is `74f6230ffcffcbc43e11bf11cfa1663c7336ce51`.
Portfolio heading, introduction and request panel share a centered responsive
780px width and matching edges. Assistant display credits can wrap. Copy,
artwork, markup, reading order and section padding are preserved. The request
remains a non-executing preview with disabled creation.

The 255-test regression suite passed for the alignment change. After the final
credit-wrapping adjustment, all 9 branding tests and the browser matrix passed.
The matrix covered 1440x900, 390x844, 320x700, 1440x400 and 320px with a 200% root
font size: matching widths/edges, no horizontal overflow or footer overlap,
local artwork, label association, keyboard order and visible focus. A full
synthetic report built; homepage, collection and About links/assets resolve.
These are implementation checks, not GitHub approval or consumer integration.
No independent implementation review is claimed.

The previous session created the Fix worktree but continued from a session rooted
in `trunk`. Its 134 local review files were subsequently moved unchanged into
that Fix worktree's ignored `.yap/local/`, with SHA-256 inventory comparison;
17 homepage/collection/About links and assets were checked after relocation.
Optional ignored `.yap/cfg/session.md` supplies exact local review navigation.
The owner approved the session-boundary correction; this closeout changes
engineering records only and adds no runtime work.

#17's accepted implementation was `d9c721e`, merged as `ce721ff` through PR #19.
#15 was accepted at `a3c7f09`, merged as `f8d2d3b` through PR #16. Their Issues
remain Done. German remains the delivered interface baseline; #6 owns localization.
Optional assistant branding supplies display metadata only, without activating
a provider. Aspirations default to `pfo/asp`, with optional instance-relative
`sources.aspirations`; the [authoring guide](../doc/authoring.md#objectives-and-key-results)
owns that accepted contract. No implicit `pfo/okr` fallback is delivered.

</details>
