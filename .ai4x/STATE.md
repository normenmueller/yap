# Return point — Issue #25 implementation checkpoint; terminal restart

The owner approved [#25](https://github.com/normenmueller/yap/issues/25)'s refined
scope on October 30, 2026. Work remains on `fix/25-yapics-cards`, based on verified
`trunk` revision `2dfa38c173135c5d0d47a2623417dccae5be0ded`. The owner now needs a
terminal restart and explicitly authorized resuming this same session for that
restart; the ordinary fresh-session boundaries remain unchanged.

The current implementation restores the two full collection cards and separate
native Need disclosures. Optional `yap.json` `illustrative_cards` inputs supply
per-card Need paragraphs, optional sender/recipient, and fixed growth labels.
Absent values are omitted, external input is validated/escaped, and paragraphs
retain their language. The change includes mobile spacing, enlarged-title wrapping
and a keyboard-scrollable region containing both the byline and Need text.
The user guide owns the exact supported format and editing instructions.

Verification against the implementation tree before this checkpoint: all 317
regression tests pass on Python 3.15.2/PyYAML 6.0.3. Pinned mypy 2.4.0 passes the
strict gate (four source files, including its positive fixture); six invalid
static calls are rejected. An independent nonauthor reviewed code, input
semantics, types, documentation and regression logic. Its one actionable finding,
a long byline displacing the Need body, was fixed and independently rechecked at
320/390px with 16/32px root fonts; the entire bubble content stays keyboard
scrollable without horizontal document overflow. This is scoped evidence, not
whole-application certification or owner acceptance.

Next: resume in this worktree, verify branch/status, and finish the real synthetic
full build, incremental rebuild, portable export, local links, desktop/mobile
visual inspection and native keyboard/JavaScript-disabled interaction checks.
The first full-build attempt stopped on an invalid priority in the temporary
synthetic fixture, before rendering. The fixture helper now omits that invalid
priority; rerun setup and build without changing application validation.
Then obtain the final independent evidence/revision review and deliver an
issue-linked PR with the required owner review request. No implementation has
been accepted and merge is not authorized. After reference use, remove only the
owner-supplied temporary reference directory as explicitly requested; optional
ignored session navigation retains its exact location. No reference source was
edited. Keep private navigation and authored reference content out of commits.

The Issue owns current scope/next action; the Project owns status/order. Preserve
other items and the accepted architecture/backlog boundaries below.

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
registrations; they were left unchanged. Their remote state was not reverified. BEHAVIOR now states the cleanup rule generically, without fixed folder
names: remove empty worktree collection directories and recreate them when needed.
Ignored/private artifacts were preserved and verified before removal; archived
configuration, virtual environments and old navigation are historical, not active.

The earlier backlog assessment recommended #8, actual quip identification, as a
concrete product case with its required typed boundaries. The owner has now selected
#25 instead; that recommendation does not override the selection. #5 remains Paused; #6/#11 deferrals and
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
