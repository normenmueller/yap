# Return point — #15 accepted and merged; await owner direction

[#15](https://github.com/normenmueller/yap/issues/15) is complete. The owner
`normenmueller` approved [PR #16](https://github.com/normenmueller/yap/pull/16)
at `a3c7f09`; it was merged into `trunk` as `f8d2d3bc16d675786e7d6bd75ea439526631f25d`
on October 26, 2026. The Issue is closed. Verify actual Git/remote state before
continuing. The accepted application baseline now includes #15 as well as
#1 / merged PR #2. Subsequent completion-note changes are memory only.

Next: report this completed delivery and wait for the owner's next work choice.
No next implementation item or consumer revision has been selected. Existing
Project order remains unchanged. Preserve the separate architecture work and
local development evidence; do not migrate an instance as part of this closeout.

The current Python application defaults to `pfo/asp`, with an optional
instance-relative `sources.aspirations` setting in `yap.json`. Selected sources
share reading, validation, change detection and publication-reference handling.
There is no implicit `pfo/okr` lookup or source creation. Instances still using
that path need their own explicit selection or manual move/reference repair.
The [authoring guide](../doc/authoring.md#objectives-and-key-results) owns usage;
#15 and PR #16 own the accepted scope and delivery evidence.

Verification at implementation revision `cf57907`: all 254 regression tests
passed, together with real HTML/PDF/browser and incremental-output checks on four
synthetic instances. Source/configuration bytes and saved/unsaved perspectives
were preserved during normal operations. Independent AI implementation review
found no unresolved findings after corrections and rechecks. The approved head
and merge do not change those implementation bytes. This application acceptance
does not establish integration in any consumer; a consumer must explicitly select
its revision and verify its own outputs.

[#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14) remains separate
on `docs/3-architecture`. Its TypeScript and broader directory contracts remain
proposals. #4 still needs its own approved foundation scope; README work remains
#13. BEHAVIOR owns recovery, reviewer requests and acceptance boundaries.
