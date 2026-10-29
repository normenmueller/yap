# Return point — resume #3 after #18 completion

The owner approved [PR #22](https://github.com/normenmueller/yap/pull/22) at
`0c2a7c5` on October 29, 2026. It merged into `trunk` as `13da252`.
[#18](https://github.com/normenmueller/yap/issues/18) is closed as completed;
the yap Project marks it Done. The owner selected #3 as the next work item.

This fresh `trunk` preparation session verified the existing clean
`docs/3-architecture` branch and matching worktree at `9284173`; the accepted
`trunk` baseline was `70552d0` before this handoff. Reuse that worktree and
preserve draft PR #14 and its review history.

End/delete this preparation session. Start a fresh Codex CLI session, without
resume, in `docs/3-architecture`. Its first authorized work is to verify and merge
the then-current `trunk`, including accepted #17, #20 and #18, while preserving
#3's architecture proposal and return point. Reconcile the current BEHAVIOR rules
and source-owned workspace contract; do not replace #3's STATE with trunk's
handoff. Then continue #3's design discussion and agree the first testable
foundation slice for separately scoped #4. No merge, architecture refinement,
implementation approval or consumer migration occurred in this preparation.
A status greeting reports and waits; a continuation greeting follows this return
point. BEHAVIOR owns the session boundaries.

The approved Python baseline now includes named source-owned YAML `wsp` maps,
consistent `wsp/NAME` navigation, explicit named create/attach and previewed
legacy migration. The [authoring guide](../doc/authoring.md#local-workspaces) owns
the contract; the [user guide](../doc/README.md) owns dependency setup and commands.
Consumer revision selection, dependency installation and migration remain separate
instance-owned work. No consumer revision or real user data was changed here.

The completed feature branch was deleted locally and remotely, its worktree was
removed, and empty `feat/`/`fix/` parent directories were removed. Ignored/private
material was preserved with matching inventories before cleanup. Optional ignored
`.yap/cfg/session.md` supplies exact local review navigation.

[#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14) remains separate
on `docs/3-architecture`; preserve that work and its return point. TypeScript and
broader architecture remain proposals. #4 and #13 are not selected here.
Previously accepted #20 / PR #21, #17 / PR #19, #15 / PR #16 and #1 / PR #2 remain
part of the baseline.

<details>
<summary>Implementation, verification and preservation evidence</summary>

The runtime change is `5dec43a`; approved PR head `0c2a7c5` adds the reviewed
recovery record. The merge tree matches that approved head. The full suite passed
281 tests with browser access; after two additional CLI tests, all six CLI tests
passed. The architecture reviewer independently passed 60 focused tests.
Independent architecture/filesystem reviews had no remaining findings after
fixes for YAML editing, case collisions, navigation cycles and metadata placement.

A full synthetic report/export built successfully. Checks covered 68 site/export
files, including seven PDFs per copy via text extraction, plus the model cache:
no workspace-path or target-content markers. Site/export SHA-256 inventories
matched. These runtime checks are reused for this records-only closeout.

All 1,646 ignored regular files, ten symlinks and 197 directories were preserved
under trunk's ignored retired development evidence. SHA-256 contents, file modes
and symlink targets matched the originals before removal. The portable report
remains reviewable; archived navigation/configuration is historical, not authority.

</details>
