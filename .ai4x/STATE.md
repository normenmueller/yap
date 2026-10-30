# Return point — Issue #27 in visual refinement after owner feedback

The owner approved the original placement scope of
[#27](https://github.com/normenmueller/yap/issues/27), implemented as `5ec0872`
and delivered in [PR #28](https://github.com/normenmueller/yap/pull/28).
The owner has not accepted that result: live review found the composition restless,
the relocated definition out of place and the area below the input incomplete.
On October 30, 2026 the owner requested visual alternatives, including radical
options, while retaining yap's lean, modern, clear and understated style.
The owner also requested a discreet homepage explanation of “to yap ≈ quasseln”,
suggesting a tooltip on “yap” in the footer. Concepts show hover/focus help; a later
implementation must retain the existing footer About navigation.

Three comparison concepts explore a dialogue-first layout, a single merged
introduction with a short closing line, and a two-column desktop composition that
stacks on mobile. They retain the product palette and identity while proposing
shorter copy and fewer separators. These are design proposals in ignored local
evidence, not accepted copy or an implemented replacement. Application code and
consumer revisions are unchanged by this exploration.

Next: support the owner's comparison and choice of design/copy, then refine and
obtain approval of the changed implementation scope before revising the application.
The Issue owns scope/next action and the PR link; the
[application Project](https://github.com/users/normenmueller/projects/5) owns live
status/order. Verify both on recovery. Existing PR acceptance and merge remain
pending; do not start another Issue or merge from the original scope approval.
BEHAVIOR owns review, merge, cleanup and session boundaries. Existing holds and
deferrals remain effective.

<details>
<summary>Issue #27 implementation, verification and limits</summary>

The actual issue worktree, branch, instructions and write scope were verified.
Preparation commit `dacf295` was present locally and on both remote `trunk` and
`fix/27-yapic-explanation`; the issue session started from this handoff.
The owner's scope approval was recorded in #27 and only its Project status was
advanced through Ready to In progress. Assignees, other item states/order and
existing holds/deferrals are preserved.

At implementation `5ec0872`, all 317 regressions passed: 316 in the full suite,
with the sole sandbox-blocked Chrome startup test passing in an isolated rerun
with browser access. The pinned mypy 2.4.0 gate passed its four declared files and
rejected six invalid calls; `home.py` remains outside that gate. The independent
source reviewer reran all nine branding checks, the browser matrix and portable
output/preservation checks and found no actionable findings. These checks do not
establish owner acceptance.

The real synthetic CLI report generated 25 site files, including five PDFs.
An unchanged repeat and the public CLI export rebuilt no outputs. Complete site
and export SHA-256 inventories matched. The exact explanation occurs once, after
the introduction and before the request section, in site, root entry and export.
All 237 inspected local href/src paths resolved (path existence, not fragment
validation). Seven authored/configuration/unsaved files retained matching SHA-256;
the synthetic private marker was absent from published files.

An isolated Chrome comparison verified unchanged computed font size, color, line
height, italic emphasis and text against the baseline. Twelve layout combinations
covered 1200/390/320px widths, 16/32px root fonts and normal/240px window heights:
paragraph/section spacing, wrapping, scrolling, no horizontal document overflow or
footer overlap. Native keyboard focus and Enter navigation to the collection passed;
six desktop/mobile/enlarged-text screenshots were visually inspected. The preview
remains a disabled creation button without form/script submission. The browser
fixture uses the default product heading and synthetic display branding. A long
custom heading already overflowed the unchanged baseline at enlarged text sizes;
this bounded change does not claim arbitrary branding layout support or a general
accessibility audit. Browser/CLI evidence remains ignored in this worktree.

</details>

<details>
<summary>Accepted Issue #25 delivery and closeout evidence</summary>

The owner approved [PR #26](https://github.com/normenmueller/yap/pull/26) at
`e14da177b385b697bc7dc4d2e93025afbc735de4` on October 30, 2026 and explicitly
authorized merge and cleanup. It merged into `trunk` as
`e12b697bf0fcbbb67b97bca7aefe91a3c117a4cd`; the merge tree matches the approved
head. [#25](https://github.com/normenmueller/yap/issues/25) is closed as completed
and its Project item is Done. Other item statuses/order and issue assignees were
preserved. Closeout changes only engineering records and metadata.

The accepted implementation restores the two full collection cards and separate
native Need disclosures. Optional `yap.json` `illustrative_cards` inputs supply
per-card paragraphs, optional sender/recipient and fixed growth labels. Missing
values are omitted; external values are validated and escaped, and authored
language is retained. The user guide owns the format and editing instructions.
This delivers neither genuine quip identification (#8) nor durable yapic
definitions/evolution (#12).

Verification at implementation revision `2b41b65`: all 317 regression tests passed on
Python 3.15.2/PyYAML 6.0.3 before the restart checkpoint. Pinned mypy 2.4.0 passed
the strict gate (four source files, including its positive fixture); six invalid
static calls were rejected. The final nonauthor independently reran the five
card-input tests, the incremental pipeline regression and both type checks.
An earlier independent finding about a long byline displacing the Need body was
fixed and rechecked; the entire bubble content is keyboard scrollable.

The real synthetic full build passed: 34 site files including seven PDFs. An
unchanged repeat rebuilt no outputs. Editing Need and a label triggered the normal
rebuild, the next repeat was up to date, and restoring the manifest reproduced the
original SHA-256 inventory. The public CLI portable export matched that inventory.
All 340 inspected local href/src paths in the root entry, site and export resolved;
this checks path existence, not fragment destinations. Eight authored, saved,
unsaved and private files were byte-for-byte preserved; a private marker was absent
from generated text, model cache and extracted PDFs.

On the exported local files, isolated Chromium-family browser checks passed at
1200/390/320px widths and 16/32px root fonts, with JavaScript enabled and disabled:
native Enter/Space disclosure, independent opening, Tab access, keyboard scrolling
to the end, card navigation and no horizontal document overflow. Pointer checks
without JavaScript confirmed Need isolation and card-body navigation at the same
six size combinations. Desktop/mobile closed/open screenshots were visually
inspected. This is scoped evidence, not whole-application certification. No application code changed during these final checks.

Closeout preserved 3,134 regular files, three symlinks and 362 directories of
ignored development/private material, verified by SHA-256 contents, modes and
symlink targets. One additional collection metadata file was preserved with
matching SHA-256 and mode before parent-directory cleanup. The local preview and evidence remain in ignored retired
development storage; archived configuration and virtual environments are historical,
not active runtime or team authority. After verifying the approved head was merged
and no unmerged work remained, the completed branch was deleted locally/remotely,
its worktree removed, and its now-empty collection directory removed. Unrelated
legacy worktrees/refs were left unchanged.

The supplied temporary reference was removed only after renewed explicit owner
approval, checking exact path/symlink boundaries and verifying absence. No reference
source was edited before removal. Private navigation and authored reference content
remain outside commits.

</details>

## Accepted Python delivery and retained backlog context

The owner approved [PR #14](https://github.com/normenmueller/yap/pull/14) at
`3fd0ba3` on October 29, 2026. It merged into `trunk` as `6862c53`; the merge tree
matches the approved head. Python remains the selected application/domain core.
[TEAM.md](TEAM.md) and [python-quality.md](python-quality.md) own the specialist
capabilities and ongoing quality method. Whole-codebase typing/10/10 is not claimed.

[#3](https://github.com/normenmueller/yap/issues/3) and
[#4](https://github.com/normenmueller/yap/issues/4) are closed as not planned for
the superseded language-replacement plan; the Project marks them Done. This does
not mark their unfinished product behavior delivered. #23 retains guided Python
create/open and stable portfolio identity, #12 durable standard/local definitions
and care references, and #24 further typed domain/model and module separation.
#8, #12, #23 and #24 remain Backlog; none is selected or Ready by this handoff.

The previous handoff records preservation and cleanup of the accepted delivery.
This preparation still found legacy local/remote-tracking refs and prunable worktree
registrations; they were left unchanged. Remote verification found no published
legacy branches. BEHAVIOR states the cleanup rule generically, without fixed
folder names: remove empty worktree collection directories and recreate them when needed.
Ignored/private artifacts were preserved and verified before removal; archived
configuration, virtual environments and old navigation are historical, not active.

The earlier backlog assessment recommended #8, actual quip identification, as a
concrete product case with its required typed boundaries. The owner has now selected
#27 instead; that recommendation does not override the selection. #5 remains Paused; #6/#11 deferrals and
#13's hold remain effective. #7/#10 retain their separately bounded effect/provider
scopes. The current quip scene is illustrative. No real collection, provider
activation, consumer revision or instance migration is selected here.

<details>
<summary>Accepted implementation and closeout evidence</summary>

The accepted implementation is `3fd0ba3`. All 312 tests passed on Python 3.15.2 with
PyYAML 6.0.3 and local browser access. Pinned mypy 2.4.0 passed strict checks for
`outputs.py`, `source_values.py` and a positive fixture; four invalid calls were
rejected. Other modules remain outside that gate; Python 3.10 syntax parsing is
not a tested interpreter-version matrix or Windows support. The runtime uses POSIX.

A real synthetic report produced 25 site files including five PDFs. Sources and
private target content were preserved, workspace markers were absent from generated
text/PDFs/model cache, portable-export SHA-256 inventories matched and a repeat
full build was up to date. The final output guard accepted the real retained work
and site trees. The 21-activity resources fixture used 26 document reads cold and
zero warm (0.9806s/0.0368s locally); this is not a full-report or scale guarantee.

Nonauthor reviewers resolved all actionable findings in the inspected source and
architecture/setup records. Their scoped context review does not certify the whole
codebase. Runtime/resources/tests match the approved delivery; this closeout only
updates engineering records, issue/project metadata and local preservation/cleanup.
Reuse the valid accepted checks rather than claiming a new regression run.

Preservation verified 3,093 regular files, four symlinks and 368 directories by
SHA-256 contents, modes and symlink targets. One additional collection-directory
metadata file was preserved with matching SHA-256 and mode before parent cleanup.
Private artifacts remain ignored under the application's retired development
evidence; no private content or machine paths are published in this handoff.

</details>
