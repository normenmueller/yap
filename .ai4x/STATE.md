# Return point — fresh trunk session after #18 completion

The owner approved [PR #22](https://github.com/normenmueller/yap/pull/22) at
`0c2a7c5` on October 29, 2026. It merged into `trunk` as `13da252`.
[#18](https://github.com/normenmueller/yap/issues/18) is closed as completed;
the yap Project marks it Done. No next engineering Issue has been selected.

End/delete the completed feature session. Start a fresh Codex CLI session in
`trunk`, without resume, and read the entry records. A status greeting reports
the observed state and waits. A continuation greeting recovers this completion
state; agree the next selected Issue with the owner before preparation. The
fresh trunk session only verifies the selection, base and matching issue-linked
branch/worktree and records its handoff. Then use a separate fresh Issue session.
BEHAVIOR owns those session boundaries; this closeout starts no further work.

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
